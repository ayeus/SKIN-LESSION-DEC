"""Explicit table-key relationships; no assumption that rows equal patients."""
import pandas as pd
from .tabular import clean_json

def inspect(child,parent,child_key,parent_key):
    if child_key not in child or parent_key not in parent:raise ValueError('Map keys to existing columns')
    target=parent[parent_key]
    if target.isna().any() or target.duplicated().any():raise ValueError('Parent key must be unique and nonmissing; do not silently deduplicate patients or encounters')
    source=child[child_key];known=set(target)
    present=source.notna();matched=present & source.isin(known)
    counts=source[present].value_counts()
    return clean_json({'child_rows':len(child),'parent_rows':len(parent),'child_key':child_key,'parent_key':parent_key,
        'matched_child_rows':int(matched.sum()),'unmatched_nonmissing_child_rows':int((present&~matched).sum()),'missing_child_keys':int((~present).sum()),
        'parents_referenced':int(source[matched].nunique()),'parents_without_children':int((~target.isin(set(source[present]))).sum()),
        'child_count_distribution':{str(int(k)):int(v) for k,v in counts.value_counts().sort_index().items()},
        'limitation':'Explicit many-to-one key membership only. Repeated child keys are retained; they may represent legitimate encounters/events. No identity linkage beyond the supplied authorized keys.'})
