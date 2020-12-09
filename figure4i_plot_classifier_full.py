#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#%%
"""
Plot the results from the classification of lab by loading in the .pkl files generated by
figure3f_decoding_lab_membership_basic and figure3f_decoding_lab_membership_full

Guido Meijer
18 Jun 2020
"""

import pandas as pd
import numpy as np
import seaborn as sns
from os.path import join
import matplotlib.pyplot as plt
from paper_behavior_functions import seaborn_style, figpath, load_csv, FIGURE_WIDTH, FIGURE_HEIGHT

# Settings
FIG_PATH = figpath()
colors = [[1, 1, 1], [1, 1, 1], [0.6, 0.6, 0.6]]
seaborn_style()

# Load in results from csv file
decoding_result = load_csv('classification_results', 'classification_results_full_bayes.pkl')

# Calculate if decoder performs above chance
chance_level = decoding_result['original_shuffled'].mean()
significance = np.percentile(decoding_result['original'], 2.5)
sig_control = np.percentile(decoding_result['control'], 0.001)
if chance_level > significance:
    print('Classification performance not significanlty above chance')
else:
    print('Above chance classification performance!')

    # %%

f, ax1 = plt.subplots(1, 1, figsize=(FIGURE_WIDTH/5, FIGURE_HEIGHT))
sns.violinplot(data=pd.concat([decoding_result['control'],
                               decoding_result['original_shuffled'],
                               decoding_result['original']], axis=1),
               palette=colors, ax=ax1)
ax1.plot([-1, 3.5], [chance_level, chance_level], '--', color='k', zorder=-10)
ax1.set(ylabel='Decoding (F1 score)', xlim=[-0.8, 2.4], ylim=[-0.1, 0.62])
ax1.set_xticklabels(['Positive\ncontrol', 'Shuffle', 'Decoding\nof lab'],
                    rotation=90, ha='center')
plt.tight_layout()
sns.despine(trim=True)

plt.savefig(join(FIG_PATH, 'figure4i_decoding.pdf'))
plt.savefig(join(FIG_PATH, 'figure4i_decoding.png'), dpi=300)
