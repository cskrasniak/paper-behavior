"""
Plot full psychometric functions as a function of choice history,
and separately for 20/80 and 80/20 blocks
"""

import pandas as pd
import numpy as np
import sys
import os
import time
import matplotlib.pyplot as plt
import seaborn as sns
from paper_behavior_functions import query_subjects
import datajoint as dj
from IPython import embed as shell  # for debugging
from math import ceil
# from figure_style import seaborn_style

# import wrappers etc
from ibl_pipeline import reference, subject, action, acquisition, data, behavior
from ibl_pipeline.utils import psychofit as psy
from dj_tools import *
from paper_behavior_functions import *

# INITIALIZE A FEW THINGS
seaborn_style()
figpath = figpath()
pal = group_colors()
institution_map, col_names = institution_map()

# ================================= #
# GRAB ALL DATA FROM DATAJOINT
# 3 days before and 3 days after starting biasedChoiceWorld
# ================================= #

use_sessions, use_days = query_sessions_around_criterion(criterion='biased',
                                                         days_from_criterion=[
                                                             2, 3],
                                                         as_dataframe=False)
# restrict by list of dicts with uuids for these sessions
b = use_sessions * subject.Subject * subject.SubjectLab * reference.Lab * \
    behavior.TrialSet.Trial
# reduce the size of the fetch
b2 = b.proj('institution_short', 'subject_nickname', 'task_protocol',
            'trial_stim_contrast_left', 'trial_stim_contrast_right', 'trial_response_choice',
            'task_protocol', 'trial_stim_prob_left', 'trial_feedback_type')
bdat = b2.fetch(order_by='institution_short, subject_nickname, session_start_time, trial_id',
                format='frame').reset_index()
behav = dj2pandas(bdat)
behav['institution_code'] = behav.institution_short.map(institution_map)
# split the two types of task protocols (remove the pybpod version number
behav['task'] = behav['task_protocol'].str[14:20]

# remove weird contrast levels
tmpdat = behav.groupby(['signed_contrast'])['choice'].count().reset_index()
removecontrasts = tmpdat.loc[tmpdat['choice'] < 100, 'signed_contrast']
behav = behav[~behav.signed_contrast.isin(removecontrasts)]

# ================================= #
# PREVIOUS CHOICE - SUMMARY PLOT
# ================================= #

behav['previous_name'] = behav.previous_outcome_name + \
    ', ' + behav.previous_choice_name

# plot one curve for each animal, one panel per lab
fig = sns.FacetGrid(behav,
                    col='task', hue='previous_name',
                    sharex=True, sharey=True, aspect=1, palette='Paired',
                    hue_order=['post_error, right', 'post_correct, right',
                               'post_error, left', 'post_correct, left'])
fig.map(plot_psychometric, "signed_contrast",
        "choice_right", "subject_nickname").add_legend()
tasks = ['Unbiased task\n(level 1)', 'Biased task\n(level 2)']
for axidx, ax in enumerate(fig.axes.flat):
    ax.set_title(tasks[axidx], color='k', fontweight='bold')
fig._legend.set_title('Previous choice')
fig.set_axis_labels('Signed contrast (%)', 'Rightward choice (%)')
fig.despine(trim=True)
fig.savefig(os.path.join(figpath, "figure4d_history_psychfuncs.pdf"))
fig.savefig(os.path.join(figpath, "figure4d_history_psychfuncs.png"), dpi=600)
plt.close('all')

# ================================= #
# DEFINE HISTORY SHIFT FOR LAG 1
# ================================= #

print('fitting psychometric functions...')
pars = behav.groupby(['institution_code', 'subject_nickname', 'task',
                      'previous_choice_name', 'previous_outcome_name']).apply(fit_psychfunc).reset_index()

# instead of the bias in % contrast, take the choice shift at x = 0
# now read these out at the presented levels of signed contrast
pars2 = pd.DataFrame([])
xvec = behav.signed_contrast.unique()
for index, group in pars.groupby(['institution_code', 'subject_nickname', 'task',
                                  'previous_choice_name', 'previous_outcome_name']):
    # expand
    yvec = psy.erf_psycho_2gammas([group.bias.item(),
                                   group.threshold.item(),
                                   group.lapselow.item(),
                                   group.lapsehigh.item()], xvec)
    group2 = group.loc[group.index.repeat(
        len(yvec))].reset_index(drop=True).copy()
    group2['signed_contrast'] = xvec
    group2['choice'] = 100 * yvec
    # add this
    pars2 = pars2.append(group2)

# only pick psychometric functions that were fit on a reasonable number of trials...
pars2 = pars2[(pars2.ntrials > 100) & (pars2.signed_contrast == 0)]

# compute history-dependent bias shift
pars3 = pd.pivot_table(pars2, values='choice',
                       index=['institution_code', 'subject_nickname',
                              'task', 'previous_outcome_name'],
                       columns=['previous_choice_name']).reset_index()
pars3['history_shift'] = pars3.right - pars3.left
pars4 = pd.pivot_table(pars3, values='history_shift',
                       index=['institution_code', 'subject_nickname', 'task'],
                       columns=['previous_outcome_name']).reset_index()
print(pars4.describe())

# ================================= #
# STRATEGY SPACE
# ================================= #

plt.close('all')
fig, ax = plt.subplots(1, 1, figsize=[3.5, 3.5])
sns.lineplot(x='post_correct', y='post_error',
             units='subject_nickname', estimator=None, color='grey', alpha=0.3,
             data=pars4, ax=ax)
# markers; only for those subjects with all 4 conditions
num_dp = pars4.groupby(['subject_nickname'])['post_error'].count().reset_index()
sjs = num_dp.loc[num_dp.post_error == 2, 'subject_nickname'].to_list()
sns.lineplot(x='post_correct', y='post_error',
             units='subject_nickname', estimator=None, color='grey', alpha=0.5, legend=False,
             data=pars4[pars4['subject_nickname'].isin(sjs)],
             ax=ax, style='task', markers={'traini':'o', 'biased':'^'}, markersize=3)

axlim = 0.5
ax.set_xlabel("History-dependent bias shift\n($\Delta$ choice %) after correct")
ax.set_ylabel("History-dependent bias shift\n($\Delta$ choice %) after error")
ax.set(xticks=[-20, 0,20,40,60], yticks=[-20, 0,20,40,60])
sns.despine(trim=True)
fig.tight_layout()
fig.savefig(os.path.join(figpath, "figure4e_history_strategy.pdf"))
fig.savefig(os.path.join(figpath, "figure4e_history_strategy.png"), dpi=600)
plt.close("all")


plt.close('all')
fig, ax = plt.subplots(1, 1, figsize=[3.5, 3.5])
pars5 = pars4.groupby(['institution_code', 'task']).mean().reset_index()
# add one line, average per lab
sns.lineplot(x='post_correct', y='post_error', hue='institution_code', palette=pal,
    linewidth=2, legend=False, data=pars5, ax=ax)
sns.lineplot(x='post_correct', y='post_error', hue='institution_code', palette=pal,
    linewidth=2, legend=False, data=pars5, ax=ax, 
    style='task', markers={'traini':'o', 'biased':'^'}, markersize=5)

axlim = 0.5
# ax.axhline(linewidth=0.75, color='k', zorder=-500)
# ax.axvline(linewidth=0.75, color='k', zorder=-500)

ax.set_xlabel("History-dependent bias shift\n($\Delta$ choice %) after correct")
ax.set_ylabel("History-dependent bias shift\n($\Delta$ choice %) after error")
ax.set(xticks=[0,10,20,30], yticks=[0,10, 20,30])
sns.despine(trim=True)
fig.tight_layout()
fig.savefig(os.path.join(figpath, "figure4e_history_strategy_labs.pdf"))
fig.savefig(os.path.join(figpath, "figure4e_history_strategy_labs.png"), dpi=600)
plt.close("all")

