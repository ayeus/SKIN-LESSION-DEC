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
from sklearn.ensemble import RandomForestRegressor
from sklearn.inspection import permutation_importance
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
    # Secondary nonlinear exploratory model uses the same locked split, no test tuning.
    nonlinear=make_pipeline(SimpleImputer(strategy='median'),RandomForestRegressor(n_estimators=100,min_samples_leaf=3,random_state=42,n_jobs=1))
    nonlinear.fit(x.iloc[train],y.iloc[train]); forest_pred=nonlinear.predict(x.iloc[test])
    importance=permutation_importance(model,x.iloc[test],y.iloc[test],n_repeats=5,random_state=42,scoring='neg_mean_absolute_error')
    sensitivity=[]
    for column in features:
        remaining=[c for c in features if c!=column]
        if remaining:
            candidate=make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),Ridge(alpha=1))
            candidate.fit(x.iloc[train][remaining],y.iloc[train]); estimate=candidate.predict(x.iloc[test][remaining])
            sensitivity.append({'omitted_feature':column,'test_mae':mean_absolute_error(y.iloc[test],estimate)})
    diagnostics={'residual_mean':float(np.mean(residual)),'residual_std':float(np.std(residual)),'feature_correlation':x.corr().to_dict(),
        'confounding_note':'Coefficients depend on the supplied adjustment set. Unmeasured confounding, selection bias and measurement error remain possible.'}
    return clean_json({'descriptive':profile(df),'model':'Standardized ridge regression, alpha=1, seed=42',
        'nonlinear_comparison':{'model':'Random forest, 100 trees, min leaf=3; no held-out tuning','test_mae':mean_absolute_error(y.iloc[test],forest_pred),'test_rmse':float(np.sqrt(mean_squared_error(y.iloc[test],forest_pred)))},
        'permutation_importance':{c:{'mean_mae_increase':float(importance.importances_mean[i]),'std':float(importance.importances_std[i])} for i,c in enumerate(features)},
        'sensitivity_leave_one_feature_out':sensitivity,'diagnostics':diagnostics,
        'train_rows':len(train),'test_rows':len(test),'mae':mean_absolute_error(y.iloc[test],pred),'rmse':np.sqrt(mean_squared_error(y.iloc[test],pred)),'r2':r2_score(y.iloc[test],pred),
        'coefficients':dict(zip(features,model[-1].coef_.tolist())),'observed':y.iloc[test].tolist(),'predicted':pred.tolist(),'residuals':residual.tolist(),
        'limitation':'Unweighted observational exploratory associations; no causal claims. User must justify adult inclusion, outcome units, confounders and repeated-person grouping. Survey population estimates unsupported.'})


def strategic(df,p):
    """Explicitly mapped historical aggregates; no assumed universal EHR schema."""
    data=df.copy(); date=p.get('date_column'); group=p.get('group_column'); count=p.get('count_column')
    if date:
        if date not in data: raise ValueError('Unknown date column')
        dates=pd.to_datetime(data[date],format=p.get('date_format','%Y-%m-%d'),errors='raise')
        if dates.isna().any(): raise ValueError('Mapped dates contain missing values')
        if p.get('start_date'): data=data.loc[dates>=pd.Timestamp(p['start_date'])]; dates=dates.loc[data.index]
        if p.get('end_date'): data=data.loc[dates<=pd.Timestamp(p['end_date'])]; dates=dates.loc[data.index]
        data=data.assign(_period=dates.dt.to_period('M').astype(str))
    if count:
        if count not in data: raise ValueError('Unknown observed count column')
        observed=pd.to_numeric(data[count],errors='raise')
        if observed.isna().any() or (observed<0).any() or not np.isfinite(observed).all(): raise ValueError('Observed counts must be finite and nonnegative')
        data=data.assign(_count=observed)
    else: data=data.assign(_count=1)
    output={'rows_selected':len(data),'observed_total':float(data._count.sum()),'definition':f'Sum of mapped {count}' if count else 'Count of source rows; rows are NOT assumed to be unique patients or encounters.'}
    if date: output['monthly_trend']=[{'date':k,'count':float(v)} for k,v in data.groupby('_period')._count.sum().items()]
    if group:
        if group not in data: raise ValueError('Unknown grouping column')
        output['distribution']={str(k):float(v) for k,v in data.groupby(group,dropna=False)._count.sum().items()}
    output['quality']=profile(data.drop(columns=['_count','_period'],errors='ignore'))
    output['limitation']='Observed descriptive aggregates only. Schema mappings define meaning; row totals are not automatically patient counts. No causal or strategic effectiveness claims.'
    return clean_json(output)
