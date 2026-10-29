import math
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import train_test_split, GroupShuffleSplit
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from .tabular import clean_json, profile

def forecast(df,p):
    date=p.get('date_column','date'); count=p.get('count_column','count')
    if date not in df or count not in df: raise ValueError('Map date_column and count_column to observed daily data')
    dates=pd.to_datetime(df[date],format=p.get('date_format','%Y-%m-%d'),errors='raise')
    values=pd.to_numeric(df[count],errors='raise')
    if dates.isna().any() or values.isna().any() or not np.isfinite(values).all() or (values<0).any(): raise ValueError('Dates/counts must be present; counts finite and nonnegative')
    if not (dates==dates.dt.normalize()).all(): raise ValueError('Daily observations must use dates without times')
    ordered=pd.Series(values.to_numpy(),index=dates).sort_index()
    if ordered.index.duplicated().any(): raise ValueError('Duplicate daily dates: aggregate with documented policy first')
    if len(ordered)<28: raise ValueError('At least 28 complete daily observations are required for baseline comparison')
    if not ordered.index.equals(pd.date_range(ordered.index.min(),ordered.index.max(),freq='D')): raise ValueError('Missing days; do not silently interpret missing observations as zero')
    horizon=int(p.get('horizon',7))
    if not 1<=horizon<=90: raise ValueError('horizon must be 1–90 days')
    y=ordered.to_numpy(dtype=float); cut=max(14,int(len(y)*.8)); train,test=y[:cut],y[cut:]
    # Rolling one-step evaluation: each validation origin sees only earlier observations.
    predictions={name:[] for name in ('last_value','weekly_seasonal','rolling_mean')}
    for i in range(cut,len(y)):
        predictions['last_value'].append(y[i-1]); predictions['weekly_seasonal'].append(y[i-7]); predictions['rolling_mean'].append(y[i-7:i].mean())
    metrics={name:{'mae':mean_absolute_error(test,v),'rmse':float(np.sqrt(mean_squared_error(test,v)))} for name,v in predictions.items()}
    # Select on validation. No independent test estimate is claimed.
    selected=min(metrics,key=lambda n:metrics[n]['mae']); history=list(y); future=[]
    for _ in range(horizon):
        v=history[-1] if selected=='last_value' else history[-7] if selected=='weekly_seasonal' else float(np.mean(history[-7:]))
        future.append(float(v)); history.append(v)
    errors=np.abs(test-np.array(predictions[selected])); radius=float(np.quantile(errors,.9))
    dates_future=pd.date_range(ordered.index[-1]+pd.Timedelta(days=1),periods=horizon,freq='D')
    result={'selected':selected,'validation_metrics':metrics,'validation_protocol':'Rolling one-step temporal validation, used for model selection; no independent test. Multi-step forecast error may be larger.',
        'observed':[{'date':d.isoformat(),'count':v} for d,v in ordered.items()],
        'forecast':[{'date':d.isoformat(),'count':v,'lower':max(0,v-radius),'upper':v+radius} for d,v in zip(dates_future,future)],
        'uncertainty':'Empirical 90th-percentile absolute one-step validation residual band; not a calibrated multi-step prediction interval.',
        'weekday_means':ordered.groupby(ordered.index.dayofweek).mean().to_dict()}
    capacity=p.get('patients_per_staff_per_shift')
    if capacity is not None:
        capacity=float(capacity)
        if not np.isfinite(capacity) or capacity<=0: raise ValueError('Explicit capacity assumption must be finite and positive')
        result['scenario']={'assumption_patients_per_staff_per_shift':capacity,'staff_per_shift':[math.ceil(v/capacity) for v in future],
            'label':'User-defined capacity scenario; ignores skill mix, shift coverage and queueing. Not a staffing prescription.'}
    return clean_json(result)

def numeric_matrix(df,columns):
    if not columns or not set(columns)<=set(df): raise ValueError('Select existing numeric feature columns')
    x=df[columns].apply(pd.to_numeric,errors='raise').replace([np.inf,-np.inf],np.nan)
    if x.isna().all().any(): raise ValueError('All-missing feature cannot be modeled')
    return x

def reduce(df,p):
    x=numeric_matrix(df,p.get('features',[]))
    if len(x)<4: raise ValueError('At least four observations required')
    dims=int(p.get('dimensions',2)); method=p.get('method','pca')
    if dims not in (2,3) or dims>min(x.shape): raise ValueError('Dimensions must be 2 or 3 and fit the matrix shape')
    scaled=make_pipeline(SimpleImputer(strategy='median'),StandardScaler()).fit_transform(x)
    if method=='pca':
        model=PCA(n_components=dims); embedding=model.fit_transform(scaled); extra={'explained_variance_ratio':model.explained_variance_ratio_.tolist(),'loadings':model.components_.tolist()}
    elif method=='tsne':
        perplexity=float(p.get('perplexity',min(30,len(x)-1)))
        if not 0<perplexity<len(x): raise ValueError('Perplexity must be positive and smaller than sample count')
        embedding=TSNE(n_components=dims,perplexity=perplexity,random_state=42,init='pca',learning_rate='auto').fit_transform(scaled); extra={}
    else: raise ValueError('Supported methods: pca, tsne. UMAP is not installed.')
    return {'method':method,'coordinates':embedding.tolist(),'features':list(x.columns),**extra,'limitation':'Exploratory geometry does not establish clinical validity. Imputation/scaling are fitted on this exploratory dataset.'}

def research(df,p):
    features=p.get('features',[]); target=p.get('target')
    if target in features: raise ValueError('Outcome must not appear in predictors')
    if not target or target not in df: raise ValueError('Select an observed numeric outcome')
    x=numeric_matrix(df,features); y=pd.to_numeric(df[target],errors='raise')
    valid=y.notna() & np.isfinite(y); x=x.loc[valid]; y=y.loc[valid]
    if len(y)<20: raise ValueError('At least twenty observed outcomes required for exploratory held-out modeling')
    group=p.get('group_column')
    if group:
        if group not in df or df.loc[valid,group].isna().any(): raise ValueError('Valid group column required')
        train,test=next(GroupShuffleSplit(n_splits=1,test_size=.25,random_state=42).split(x,y,df.loc[valid,group]))
    else: train,test=train_test_split(np.arange(len(y)),test_size=.25,random_state=42)
    model=make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),Ridge(alpha=1))
    model.fit(x.iloc[train],y.iloc[train]); pred=model.predict(x.iloc[test]); residual=y.iloc[test].to_numpy()-pred
    return clean_json({'descriptive':profile(df),'model':'Standardized ridge regression, alpha=1, seed=42',
        'train_rows':len(train),'test_rows':len(test),'mae':mean_absolute_error(y.iloc[test],pred),'rmse':np.sqrt(mean_squared_error(y.iloc[test],pred)),'r2':r2_score(y.iloc[test],pred),
        'coefficients':dict(zip(features,model[-1].coef_.tolist())),'observed':y.iloc[test].tolist(),'predicted':pred.tolist(),'residuals':residual.tolist(),
        'limitation':'Unweighted observational exploratory associations; no causal claims. User must justify adult inclusion, outcome units, confounders and repeated-person grouping. Survey population estimates unsupported.'})
