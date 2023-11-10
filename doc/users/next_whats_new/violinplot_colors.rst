``violinplot`` now accepts color arguments
-------------------------------------------

The ``~.Axes.violinplot`` constructor now accepts ``color``, ``fillcolor``,
and ``linecolor`` as input arguments. This means that users can set the color
of violinplots as they make them, rather than setting the color of individual
objects aftewards. 

Example
~~~~~~~
data = [sorted(np.random.normal(0, std, 100)) for std in range(1, 5)]
    
fig, ax = plt.subplots(2,3,figsize=(9,6))

# Previous Method
parts0 = ax[0,0].violinplot(data, showmeans = True, showextrema = True, showmedians = True)
for pc in parts0['bodies']:
    pc.set_facecolor('r')
for partname in ('cbars', 'cmins', 'cmaxes', 'cmeans', 'cmedians'):
    if partname in parts0:
        pc = parts0[partname]
        pc.set_edgecolor('r')

parts1 = ax[0,1].violinplot(data, showmeans = True, showextrema = True, showmedians = True)
for pc in parts1['bodies']:
    pc.set_facecolor('r')

parts2 = ax[0,2].violinplot(data, showmeans = True, showextrema = True, showmedians = True)
for partname in ('cbars', 'cmins', 'cmaxes', 'cmeans', 'cmedians'):
    if partname in parts2:
        pc = parts2[partname]
        pc.set_edgecolor('r')

# New method
ax[1,0].violinplot(data, color = 'r', showmeans = True, showextrema = True, showmedians = True)
ax[1,1].violinplot(data, fillcolor = 'r', showmeans = True, showextrema = True, showmedians = True)
ax[1,2].violinplot(data, linecolor = 'r', showmeans = True, showextrema = True, showmedians = True)