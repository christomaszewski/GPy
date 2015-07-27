# Copyright (c) 2012-2015, GPy authors (see AUTHORS.txt).
# Licensed under the BSD 3-clause license (see LICENSE.txt)

try:
    import Tango
    import pylab as pb
except:
    pass
import numpy as np
from base_plots import gpplot, x_frame1D, x_frame2D
from ...models.gp_coregionalized_regression import GPCoregionalizedRegression
from ...models.sparse_gp_coregionalized_regression import SparseGPCoregionalizedRegression
from scipy import sparse
from ...core.parameterization.variational import VariationalPosterior

def plot_fit(model, plot_limits=None, which_data_rows='all',
        which_data_ycols='all', fixed_inputs=[],
        levels=20, samples=0, fignum=None, ax=None, resolution=None,
        plot_raw=False,
        linecol=Tango.colorsHex['darkBlue'],fillcol=Tango.colorsHex['lightBlue'], Y_metadata=None, data_symbol='kx',
        apply_link=False, samples_f=0, plot_uncertain_inputs=True, predict_kw=None):
    """
    Plot the posterior of the GP.
      - In one dimension, the function is plotted with a shaded region identifying two standard deviations.
      - In two dimsensions, a contour-plot shows the mean predicted function
      - In higher dimensions, use fixed_inputs to plot the GP  with some of the inputs fixed.

    Can plot only part of the data and part of the posterior functions
    using which_data_rowsm which_data_ycols.

    :param plot_limits: The limits of the plot. If 1D [xmin,xmax], if 2D [[xmin,ymin],[xmax,ymax]]. Defaluts to data limits
    :type plot_limits: np.array
    :param which_data_rows: which of the training data to plot (default all)
    :type which_data_rows: 'all' or a slice object to slice model.X, model.Y
    :param which_data_ycols: when the data has several columns (independant outputs), only plot these
    :type which_data_rows: 'all' or a list of integers
    :param fixed_inputs: a list of tuple [(i,v), (i,v)...], specifying that input index i should be set to value v.
    :type fixed_inputs: a list of tuples
    :param resolution: the number of intervals to sample the GP on. Defaults to 200 in 1D and 50 (a 50x50 grid) in 2D
    :type resolution: int
    :param levels: number of levels to plot in a contour plot.
    :type levels: int
    :param samples: the number of a posteriori samples to plot p(y*|y)
    :type samples: int
    :param fignum: figure to plot on.
    :type fignum: figure number
    :param ax: axes to plot on.
    :type ax: axes handle
    :type output: integer (first output is 0)
    :param linecol: color of line to plot.
    :type linecol:
    :param fillcol: color of fill
    :param levels: for 2D plotting, the number of contour levels to use is ax is None, create a new figure
    :param apply_link: apply the link function if plotting f (default false)
    :type apply_link: boolean
    :param samples_f: the number of posteriori f samples to plot p(f*|y)
    :type samples_f: int
    """
    #deal with optional arguments
    if which_data_rows == 'all':
        which_data_rows = slice(None)
    if which_data_ycols == 'all':
        which_data_ycols = np.arange(model.output_dim)
    #if len(which_data_ycols)==0:
        #raise ValueError('No data selected for plotting')
    if ax is None:
        fig = pb.figure(num=fignum)
        ax = fig.add_subplot(111)

    if hasattr(model, 'has_uncertain_inputs') and model.has_uncertain_inputs():
        X = model.X.mean
        X_variance = model.X.variance
    else:
        X = model.X
    Y = model.Y
    if sparse.issparse(Y): Y = Y.todense().view(np.ndarray)

    if hasattr(model, 'Z'): Z = model.Z

    if predict_kw is None:
        predict_kw = {}

    #work out what the inputs are for plotting (1D or 2D)
    fixed_dims = np.array([i for i,v in fixed_inputs])
    free_dims = np.setdiff1d(np.arange(model.input_dim),fixed_dims)
    plots = {}
    #one dimensional plotting
    if len(free_dims) == 1:

        #define the frame on which to plot
        Xnew, xmin, xmax = x_frame1D(X[:,free_dims], plot_limits=plot_limits, resolution=resolution or 200)
        Xgrid = np.empty((Xnew.shape[0],model.input_dim))
        Xgrid[:,free_dims] = Xnew
        for i,v in fixed_inputs:
            Xgrid[:,i] = v

        #make a prediction on the frame and plot it
        if plot_raw:
            m, v = model._raw_predict(Xgrid, **predict_kw)
            if apply_link:
                lower = model.likelihood.gp_link.transf(m - 2*np.sqrt(v))
                upper = model.likelihood.gp_link.transf(m + 2*np.sqrt(v))
                #Once transformed this is now the median of the function
                m = model.likelihood.gp_link.transf(m)
            else:
                lower = m - 2*np.sqrt(v)
                upper = m + 2*np.sqrt(v)
        else:
            if isinstance(model,GPCoregionalizedRegression) or isinstance(model,SparseGPCoregionalizedRegression):
                extra_data = Xgrid[:,-1:].astype(np.int)
                if Y_metadata is None:
                    Y_metadata = {'output_index': extra_data}
                else:
                    Y_metadata['output_index'] = extra_data
            m, v = model.predict(Xgrid, full_cov=False, Y_metadata=Y_metadata, **predict_kw)
            lower, upper = model.predict_quantiles(Xgrid, Y_metadata=Y_metadata)


        for d in which_data_ycols:
            plots['gpplot'] = gpplot(Xnew, m[:, d], lower[:, d], upper[:, d], ax=ax, edgecol=linecol, fillcol=fillcol)
            if not plot_raw: plots['dataplot'] = ax.plot(X[which_data_rows,free_dims], Y[which_data_rows, d], data_symbol, mew=1.5)

        #optionally plot some samples
        if samples: #NOTE not tested with fixed_inputs
            Ysim = model.posterior_samples(Xgrid, samples, Y_metadata=Y_metadata)
            print Ysim.shape
            print Xnew.shape
            for yi in Ysim.T:
                plots['posterior_samples'] = ax.plot(Xnew, yi[:,None], Tango.colorsHex['darkBlue'], linewidth=0.25)
                #ax.plot(Xnew, yi[:,None], marker='x', linestyle='--',color=Tango.colorsHex['darkBlue']) #TODO apply this line for discrete outputs.

        if samples_f: #NOTE not tested with fixed_inputs
            Fsim = model.posterior_samples_f(Xgrid, samples_f)
            for fi in Fsim.T:
                plots['posterior_samples_f'] = ax.plot(Xnew, fi[:,None], Tango.colorsHex['darkBlue'], linewidth=0.25)
                #ax.plot(Xnew, yi[:,None], marker='x', linestyle='--',color=Tango.colorsHex['darkBlue']) #TODO apply this line for discrete outputs.


        #add error bars for uncertain (if input uncertainty is being modelled)
        if hasattr(model,"has_uncertain_inputs") and model.has_uncertain_inputs() and plot_uncertain_inputs:
            if plot_raw:
                #add error bars for uncertain (if input uncertainty is being modelled), for plot_f
                #Hack to plot error bars on latent function, rather than on the data
                vs = model.X.mean.values.copy()
                for i,v in fixed_inputs:
                    vs[:,i] = v
                m_X, _ = model._raw_predict(vs)
                if apply_link:
                    m_X = model.likelihood.gp_link.transf(m_X)
                plots['xerrorbar'] = ax.errorbar(X[which_data_rows, free_dims].flatten(), m_X[which_data_rows, which_data_ycols].flatten(),
                            xerr=2 * np.sqrt(X_variance[which_data_rows, free_dims].flatten()),
                            ecolor='k', fmt=None, elinewidth=.5, alpha=.5)
            else:
                plots['xerrorbar'] = ax.errorbar(X[which_data_rows, free_dims].flatten(), Y[which_data_rows, which_data_ycols].flatten(),
                            xerr=2 * np.sqrt(X_variance[which_data_rows, free_dims].flatten()),
                            ecolor='k', fmt=None, elinewidth=.5, alpha=.5)

        #set the limits of the plot to some sensible values
        ymin, ymax = min(np.append(Y[which_data_rows, which_data_ycols].flatten(), lower)), max(np.append(Y[which_data_rows, which_data_ycols].flatten(), upper))
        ymin, ymax = ymin - 0.1 * (ymax - ymin), ymax + 0.1 * (ymax - ymin)
        ax.set_xlim(xmin, xmax)
        ax.set_ylim(ymin, ymax)

        #add inducing inputs (if a sparse model is used)
        if hasattr(model,"Z"):
            #Zu = model.Z[:,free_dims] * model._Xscale[:,free_dims] + model._Xoffset[:,free_dims]
            if isinstance(model,SparseGPCoregionalizedRegression):
                Z = Z[Z[:,-1] == Y_metadata['output_index'],:]
            Zu = Z[:,free_dims]
            z_height = ax.get_ylim()[0]
            plots['inducing_inputs'] = ax.plot(Zu, np.zeros_like(Zu) + z_height, 'r|', mew=1.5, markersize=12)



    #2D plotting
    elif len(free_dims) == 2:

        #define the frame for plotting on
        resolution = resolution or 50
        Xnew, _, _, xmin, xmax = x_frame2D(X[:,free_dims], plot_limits, resolution)
        Xgrid = np.empty((Xnew.shape[0],model.input_dim))
        Xgrid[:,free_dims] = Xnew
        for i,v in fixed_inputs:
            Xgrid[:,i] = v
        x, y = np.linspace(xmin[0], xmax[0], resolution), np.linspace(xmin[1], xmax[1], resolution)

        #predict on the frame and plot
        if plot_raw:
            m, _ = model._raw_predict(Xgrid, **predict_kw)
        else:
            if isinstance(model,GPCoregionalizedRegression) or isinstance(model,SparseGPCoregionalizedRegression):
                extra_data = Xgrid[:,-1:].astype(np.int)
                if Y_metadata is None:
                    Y_metadata = {'output_index': extra_data}
                else:
                    Y_metadata['output_index'] = extra_data
            m, v = model.predict(Xgrid, full_cov=False, Y_metadata=Y_metadata, **predict_kw)
        for d in which_data_ycols:
            m_d = m[:,d].reshape(resolution, resolution).T
            plots['contour'] = ax.contour(x, y, m_d, levels, vmin=m.min(), vmax=m.max(), cmap=pb.cm.jet)
            if not plot_raw: plots['dataplot'] = ax.scatter(X[which_data_rows, free_dims[0]], X[which_data_rows, free_dims[1]], 40, Y[which_data_rows, d], cmap=pb.cm.jet, vmin=m.min(), vmax=m.max(), linewidth=0.)

        #set the limits of the plot to some sensible values
        ax.set_xlim(xmin[0], xmax[0])
        ax.set_ylim(xmin[1], xmax[1])

        if samples:
            warnings.warn("Samples are rather difficult to plot for 2D inputs...")

        #add inducing inputs (if a sparse model is used)
        if hasattr(model,"Z"):
            #Zu = model.Z[:,free_dims] * model._Xscale[:,free_dims] + model._Xoffset[:,free_dims]
            Zu = Z[:,free_dims]
            plots['inducing_inputs'] = ax.plot(Zu[:,0], Zu[:,1], 'wo')

    else:
        raise NotImplementedError("Cannot define a frame with more than two input dimensions")
    return plots

def plot_fit_f(model, *args, **kwargs):
    """
    Plot the GP's view of the world, where the data is normalized and before applying a likelihood.

    All args and kwargs are passed on to models_plots.plot.
    """
    kwargs['plot_raw'] = True
    plot_fit(model,*args, **kwargs)

def fixed_inputs(model, non_fixed_inputs, fix_routine='median', as_list=True, X_all=False):
    """
    Convenience function for returning back fixed_inputs where the other inputs
    are fixed using fix_routine
    :param model: model
    :type model: Model
    :param non_fixed_inputs: dimensions of non fixed inputs
    :type non_fixed_inputs: list
    :param fix_routine: fixing routine to use, 'mean', 'median', 'zero'
    :type fix_routine: string
    :param as_list: if true, will return a list of tuples with (dimension, fixed_val) otherwise it will create the corresponding X matrix
    :type as_list: boolean
    """
    f_inputs = []
    if hasattr(model, 'has_uncertain_inputs') and model.has_uncertain_inputs():
        X = model.X.mean.values.copy()
    elif isinstance(model.X, VariationalPosterior):
        X = model.X.values.copy()
    else:
        if X_all:
            X = model.X_all.copy()
        else:
            X = model.X.copy()
    for i in range(X.shape[1]):
        if i not in non_fixed_inputs:
            if fix_routine == 'mean':
                f_inputs.append( (i, np.mean(X[:,i])) )
            if fix_routine == 'median':
                f_inputs.append( (i, np.median(X[:,i])) )
            else: # set to zero zero
                f_inputs.append( (i, 0) )
            if not as_list:
                X[:,i] = f_inputs[-1][1]
    if as_list:
        return f_inputs
    else:
        return X
