import plotly.graph_objects as go
import numpy as np
from PIL import Image, ImageColor
import pandas as pd
import scipy
from plotly.utils import image_array_to_data_uri
import s3fs
import dill

import streamlit as st
import streamlit_nested_layout
from streamlit_plotly_events import plotly_events
from streamlit_util import *

from util.z_score_psth import compute_group_tuning
from util.plotly_util import add_plotly_errorbar

from Home import add_unit_filter


export_folder = 'aind-behavior-data/Han/ephys/export/'
fs = s3fs.S3FileSystem(anon=False)

z_tuning_mappper = {'dQ_go_cue_before_2': dict(align_to='go_cue', time_win=[-2, 0], latent_name='relative_action_value_lr', latent_bins=np.linspace(-3, 3, 20), if_z_score_latent=True, latent_variable_offset=-1),
                    'dQ_iti_start_before_1': dict(align_to='iti_start', time_win=[-1, 0], latent_name='relative_action_value_lr', latent_bins=np.linspace(-3, 3, 20), if_z_score_latent=True),
                    'dQ_iti_start_after_2': dict(align_to='iti_start', time_win=[0, 2], latent_name='relative_action_value_lr', latent_bins=np.linspace(-3, 3, 20), if_z_score_latent=True),
                    
                    'sumQ_go_cue_before_2': dict(align_to='go_cue', time_win=[-2, 0], latent_name='total_action_value', latent_bins=np.linspace(-3, 3, 20), if_z_score_latent=True, latent_variable_offset=-1),
                    'sumQ_iti_start_before_1': dict(align_to='iti_start', time_win=[-1, 0], latent_name='total_action_value', latent_bins=np.linspace(-3, 3, 20), if_z_score_latent=True),
                    'sumQ_iti_start_after_2': dict(align_to='iti_start', time_win=[0, 2], latent_name='total_action_value', latent_bins=np.linspace(-3, 3, 20), if_z_score_latent=True),
                    
                    'rpe_go_cue_before_2': dict(align_to='go_cue', time_win=[-2, 0], latent_name='rpe', latent_bins=np.linspace(-1, 1, 20), if_z_score_latent=False, latent_variable_offset=-1),
                    'rpe_choice_after_2': dict(align_to='choice', time_win=[0, 2], latent_name='rpe', latent_bins=np.linspace(-1, 1, 20), if_z_score_latent=False),                    
                    'rpe_iti_start_before_1': dict(align_to='iti_start', time_win=[-1, 0], latent_name='rpe', latent_bins=np.linspace(-1, 1, 20), if_z_score_latent=False),
                    'rpe_iti_start_after_2': dict(align_to='iti_start', time_win=[0, 2], latent_name='rpe', latent_bins=np.linspace(-1, 1, 20), if_z_score_latent=False),
                   }


@st.experimental_memo(ttl=24*3600)
def load_z_score(file_name):
    with fs.open(export_folder + file_name) as f:
        df = pd.read_pickle(f)
        
    meta = df._metadata
    return df, meta


@st.experimental_memo(ttl=24*3600)
def plot_population_tuning(df_all, meta, if_flip_tuning=True, significance_level=None, choice_group='all_choice'):
    
    fig = go.Figure()
        
    for aoi in st.session_state.df['aoi'].index:
        if aoi not in df_all.area_of_interest.values:
            continue
    
        df_this_aoi = df_all[df_all.area_of_interest == aoi]
        
        if choice_group == 'all_choice':
            if meta['latent_name'] == 'rpe' or if_flip_tuning:
                tuning_mean, tuning_sem, selected_tuning = compute_group_tuning(df_this_aoi, 
                                                                                unit_keys=None, #df.index[df.r > 0], 
                                                                                if_z_score_firing=True,
                                                                                significance_level=significance_level,
                                                                                if_flip_tuning=if_flip_tuning,
                                                                                choice_group='all_choice')
                add_plotly_errorbar(x=tuning_mean.index, 
                                    y=tuning_mean, 
                                    err=tuning_sem, 
                                    col=st.session_state.aoi_color_mapping[aoi],
                                    hovertemplate=  '%s' % (aoi) +
                                                    '<br>n = %s' % (len(selected_tuning)) +
                                                    '<extra></extra>',
                                    fig=fig, alpha=0.2, name=aoi)
            else:  # Not flipped and not rpe, generate tuning separately for positively and negatively tuned
                sign_mapping = [['pref_l', df_this_aoi.index[df_this_aoi.r <= 0]],
                                ['pref_r', df_this_aoi.index[df_this_aoi.r > 0]], 
                                ]
                
                for condition_name, condition in sign_mapping:
                    tuning_mean, tuning_sem, selected_tuning = compute_group_tuning(df_this_aoi, 
                                                                                    unit_keys=condition,
                                                                                    if_z_score_firing=True,
                                                                                    significance_level=significance_level,
                                                                                    if_flip_tuning=False,
                                                                                    choice_group='all_choice')
                    add_plotly_errorbar(x=tuning_mean.index, 
                                        y=tuning_mean, 
                                        err=tuning_sem, 
                                        col=st.session_state.aoi_color_mapping[aoi],
                                        hovertemplate=  '%s' % (aoi) +
                                                        '<br>n = %s' % (len(selected_tuning)) +
                                                        '<extra></extra>',
                                        fig=fig, alpha=0.2, 
                                        name=f'{aoi}_{condition_name}',
                                        legend_group=f'group_{aoi}',
                                        line=dict(dash='solid' if '_r' in condition_name else 'dot')) 
            
        else:
            for choice in ['l', 'r']:
                tuning_mean, tuning_sem, selected_tuning = compute_group_tuning(df_this_aoi, 
                                                                                unit_keys=None, #df.index[df.r > 0], 
                                                                                if_z_score_firing=True,
                                                                                significance_level=None,
                                                                                if_flip_tuning=if_flip_tuning,
                                                                                choice_group=f'{choice_group}_{choice}')                    
                add_plotly_errorbar(x=tuning_mean.index, 
                                    y=tuning_mean, 
                                    err=tuning_sem, 
                                    col=st.session_state.aoi_color_mapping[aoi], 
                                    fig=fig, alpha=0.2, name=f'{aoi}_{choice}', legend_group=f'group_{aoi}',
                                    hovertemplate=  '%s' % (aoi) +
                                        '<br>n = %s' % (len(selected_tuning)) +
                                        '<extra></extra>',
                                    line=dict(dash='solid' if choice == 'r' else 'dot'))
                     
        
    fig.update_layout(
                font=dict(size=17),
                xaxis_title=f'{meta["latent_name"]} ({"z-scored" if meta["if_z_score_latent"] else "raw"}, {"flipped" if if_flip_tuning else "not flipped"})',
                yaxis_title='z-scored firing',
                title=f'{[meta[x] for x in ["align_to", "time_win"]]}',
                )
    
    return fig
    

with st.sidebar:
    add_unit_filter()
    st.session_state.sign_level = st.number_input("significant level: t >= ", 
                                                value=st.session_state.sign_level if 'sign_level' in st.session_state else 2.57, 
                                                disabled=False, step=1.0) #'significant' not in heatmap_aggr_name, step=1.0)

cols = st.columns([1, 1, 5])
z_method = cols[0].selectbox('Z-score latent variable and time epoch', z_tuning_mappper.keys(), index=0)
sign_only = cols[1].checkbox('significant only', False)

df_this_setting_all_session, z_score_meta = load_z_score(f'z_score_all_{z_method}.pkl')

unit_keys = ['subject_id', 'session', 'ins', 'unit']
df_aoi = st.session_state.df_unit_filtered[['area_of_interest'] + unit_keys].set_index(unit_keys
                                                                                       ).rename_axis([name if name != 'ins' else 'insertion_number' for name in unit_keys])
df_aoi.columns = pd.MultiIndex.from_product([df_aoi.columns, [''], ['']])
df_this_setting_all_session = df_this_setting_all_session.join(df_aoi)


# Flipped
cols = st.columns([1, 1, 1])
with cols[0]:
    st.markdown('### All choices')
    fig = plot_population_tuning(df_this_setting_all_session, 
                                 z_score_meta,
                                 significance_level=0.05 if sign_only else None,
                                 if_flip_tuning=False if 'rpe' in z_method else True, 
                                 choice_group='all_choice')
    selected = plotly_events(fig, click_event=True, hover_event=False, select_event=True, override_height=700, override_width=700)

with cols[1]:
    st.markdown('### Separated by the previous choice')
    fig = plot_population_tuning(df_this_setting_all_session, 
                                 z_score_meta, 
                                 significance_level=0.05 if sign_only else None,
                                 if_flip_tuning=False if 'rpe' in z_method else True, 
                                 choice_group='previous_choice')
    selected = plotly_events(fig, click_event=True, hover_event=False, select_event=True, override_height=700, override_width=700)

with cols[2]:
    st.markdown('### Separated by the next choice')
    fig = plot_population_tuning(df_this_setting_all_session, 
                                 z_score_meta, 
                                 significance_level=0.05 if sign_only else None,
                                 if_flip_tuning=False if 'rpe' in z_method else True, 
                                 choice_group='next_choice')
    selected = plotly_events(fig, click_event=True, hover_event=False, select_event=True, override_height=700, override_width=700)

# Non-flipped, left and right separately
if 'rpe' not in z_method:   # For rpe, it is non-flipped
    cols = st.columns([1, 1, 1])
    with cols[0]:
        st.markdown('### All choices, not flipped')
        fig = plot_population_tuning(df_this_setting_all_session, 
                                     z_score_meta, 
                                     if_flip_tuning=False, 
                                     significance_level=0.05 if sign_only else None,
                                     choice_group='all_choice')
        selected = plotly_events(fig, click_event=True, hover_event=False, select_event=True, override_height=700, override_width=750)