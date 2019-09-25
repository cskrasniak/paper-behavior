"""
TRAINING PROGRESSION FOR AN EXAMPLE MOUSE
Anne Urai, CSHL, 2019
"""

import dj_tools
from paper_behavior_functions import *
import numpy as np
import sys
import matplotlib.pyplot as plt
import seaborn as sns
import datajoint as dj
from IPython import embed as shell  # for debugging
import os
from datetime import timedelta
import matplotlib as mpl

# import wrappers etc
from ibl_pipeline import subject, behavior, acquisition
endcriteria = dj.create_virtual_module(
    'SessionEndCriteria', 'group_shared_end_criteria')  # from Miles

# grab some plotting functions from datajoint
sys.path.append("../IBL_pipeline/prelim_analyses/behavioral_snapshots")
from IBL_pipeline.prelim_analyses.behavioral_snapshots import load_mouse_data_datajoint, behavior_plots

# INITIALIZE A FEW THINGS
seaborn_style()
figpath = figpath()
plt.close('all')

# ================================= #
# pick an example mouse
# ================================= #

mouse = 'CSHL_015'
lab = 'churchlandlab'

weight_water, baseline = load_mouse_data_datajoint.get_water_weight(mouse, lab)
xlims = [weight_water.date.min() - timedelta(days=2),
         weight_water.date.max() + timedelta(days=2)]

# ================================= #
# CONTRAST HEATMAP
# ================================= #

fig, ax = plt.subplots(1, 2, figsize=(7, 2.5))
behavior_plots.plot_contrast_heatmap(mouse, lab, ax[0], xlims)
ax[1].axis('off')
ax[0].set_ylabel('Signed contrast (%)')
ax[0].set_xlabel('Training days')
ax[0].set_title('Mouse %s' % mouse)
plt.tight_layout()
fig.savefig(os.path.join(figpath, "figure3_example_contrastheatmap.png"))

# ================================================================== #
# PSYCHOMETRIC AND CHRONOMETRIC FUNCTIONS FOR EXAMPLE 3 DAYS
# ================================================================== #

b = (subject.Subject & 'subject_nickname = "%s"' % mouse) \
    * (subject.SubjectLab & 'lab_name="%s"' % lab) \
    * behavior.TrialSet.Trial \
    * acquisition.Session \
    * endcriteria.SessionEndCriteria
behav = b.fetch(order_by='session_start_time, trial_id',
                format='frame').reset_index()
print(behav)
behav = dj_tools.dj2pandas(behav)
behav['trial_start_time'] = behav.trial_start_time / 60  # in minutes
behav['correct_easy'] = behav.correct_easy * 100
behav['training_day'] = behav.days.map(
    dict(zip(list(behav.days.unique()), list(range(len(behav.days.unique()))))))

days = behav.training_day.unique()

for didx, day in enumerate(days):

    assert(day in behav.days)

    # select data from one day
    behavtmp = behav.loc[behav['training_day'] == day, :].copy()

    # PSYCHOMETRIC FUNCTIONS
    fig, ax = plt.subplots(1, 1, figsize=(2, 2))
    behavior_plots.plot_psychometric(behavtmp.rename(
        columns={'signed_contrast': 'signedContrast'}), ax=ax, color='k')
    ax.set(xlabel="Signed contrast (%)",
           ylabel="Rightward choices (%)", ylim=[0, 1])
    ax.set(title='Day %d' % day)
    sns.despine(trim=True)
    plt.tight_layout()
    fig.savefig(os.path.join(
        figpath, "figure3_example_psychfunc_day%d.png" % day), dpi=600)

    # CHRONOMETRIC FUNCTIONS
    fig, ax = plt.subplots(1, 1, figsize=(2, 2))
    behavior_plots.plot_chronometric(behavtmp.rename(
        columns={'signed_contrast': 'signedContrast'}), ax=ax, color='k')
    ax.grid(False)
    ax.set(xlabel="Signed contrast (%)", ylabel="RT (s)", ylim=[0, 1.5])
    ax.set(title='Day %d' % day)

    # rt axis scaling
    ax.set(ylim=[0.1, 1.5], yticks=[0.1, 1.5])
    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(mpl.ticker.FuncFormatter(lambda y, pos:
                                                          ('{{:.{:1d}f}}'.format(int(np.maximum(-np.log10(y), 0)))).format(y)))
    sns.despine(trim=True)
    plt.tight_layout()
    fig.savefig(os.path.join(
        figpath, "figure3_example_chronfunc_day%d.png" % day), dpi=600)

    # ================================================================== #
    # WITHIN-TRIAL DISENGAGEMENT CRITERIA
    # ================================================================== #

    plt.close('all')
    fig, ax = plt.subplots(1, 1, figsize=(4, 3))

    # RTS THROUGHOUT SESSION
    sns.scatterplot(x='trial_start_time', y='rt', style='correct', hue='correct',
                    palette={1: "#009E73", 0: "#D55E00"},
                    markers={1: 'o', 0: 'X'}, s=10, edgecolors='face',
                    alpha=.5, data=behavtmp, ax=ax, legend=False)

    # running median overlaid
    sns.lineplot(x='trial_start_time', y='rt', color='black', ci=None,
                 data=behavtmp[['trial_start_time', 'rt']].rolling(20).median(), ax=ax)
    ax.set(xlabel="Trial number", ylabel="RT (s)", ylim=[0.02, 60])
    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(mpl.ticker.FuncFormatter(lambda y, pos:
                                                          ('{{:.{:1d}f}}'.format(int(np.maximum(-np.log10(y), 0)))).format(y)))
    ax.set(xlabel="Time in session (min)", ylabel="RT (s)")

    # right y-axis with sliding performance
    # from https://stackoverflow.com/questions/36988123/pandas-groupby-and-rolling-apply-ignoring-nans
    g1 = behavtmp[['trial_start_time', 'correct_easy']]
    g2 = g1.fillna(0).copy()
    s = g2.rolling(50).sum() / g1.rolling(50).count()  # the actual computation

    ax2 = ax.twinx()
    sns.lineplot(x='trial_start_time', y='correct_easy', color='darkblue', ci=None,
                 data=s, ax=ax2)
    ax2.set(xlabel='', ylabel="Accuracy (%)",
            ylim=[0, 101], yticks=[0, 50, 100])
    ax2.yaxis.label.set_color("darkblue")
    ax2.tick_params(axis='y', colors='darkblue')

    # INDICATE THE REASON AND TRIAL AT WHICH SESSION SHOULD HAVE ENDED
    end_x = behavtmp.loc[behavtmp.trial_id == behavtmp.end_status_index.unique()[
        0], 'trial_start_time'].values[0]
    ax2.axvline(x=end_x, color='darkgrey')
    ax2.annotate(behavtmp.end_status.unique()[0], xy=(end_x, 100), xytext=(end_x, 105),
                 arrowprops={'arrowstyle': "->", 'connectionstyle': "arc3"})

    ax.set(title='Day %d' % day)
    # sns.despine(trim=True)
    plt.tight_layout()
    fig.savefig(os.path.join(
        figpath, "figure3_example_disengagement_day%d.png" % day), dpi=600)
