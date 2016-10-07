from collections import OrderedDict, namedtuple
from artemis.plotting.data_conversion import vector_length_to_tile_dims
from artemis.plotting.matplotlib_backend import get_plot_from_data, TextPlot, MovingPointPlot, Moving2DPointPlot, \
    MovingImagePlot, HistogramPlot
from artemis.plotting.plotting_backend import LinePlot, ImagePlot
from matplotlib import gridspec
from matplotlib import pyplot as plt
__author__ = 'peter'


_PlotWindow = namedtuple('PlotWindow', ['figure', 'subplots'])

_Subplot = namedtuple('Subplot', ['axis', 'plot_object'])

_DBPLOT_FIGURES = {}  # An dict<figure_name: _PlotWindow(figure, OrderedDict<subplot_name:_Subplot>)>


_DEFAULT_SIZE = None


def set_dbplot_figure_size(width, height):
    global _DEFAULT_SIZE
    _DEFAULT_SIZE = (width, height)


def get_dbplot_figure(name=None):
    return _DBPLOT_FIGURES[name].figure

def get_dbplot_subplot(name, fig_name=None):
    return _DBPLOT_FIGURES[fig_name].subplots[name].axis


def _make_dbplot_figure():

    if _DEFAULT_SIZE is None:
        fig= plt.figure()
    else:
        fig= plt.figure(figsize=_DEFAULT_SIZE)
    # fig.canvas.start_event_loop(0.1)
    return fig



def dbplot(data, name = None, plot_constructor = None, plot_mode = 'live', draw_now = True, hang = False, title=None,
           fig = None, xlabel = None, ylabel = None):
    """
    Plot arbitrary data.  This program tries to figure out what type of plot to use.

    :param data: Any data.  Hopefully, we at dbplot will be able to figure out a plot for it.
    :param name: A name uniquely identifying this plot.
    :param plot_constructor: A specialized constructor to be used the first time when plotting.  You can also pass
        certain string to give hints as to what kind of plot you want (can resolve cases where the given data could be
        plotted in multiple ways):
        'line': Plots a line plot
        'img': An image plot
        'colour': A colour image plot
        'pic': A picture (no scale bars, axis labels, etc).
    :param plot_mode: Influences how the data should be used to choose the plot type:
        'live': Best for 'live' plots that you intend to update as new data arrives
        'static': Best for 'static' plots, that you do not intend to update
        'image': Try to represent the plot as an image
    :param draw_now: Draw the plot now (you may choose false if you're going to add another plot immediately after and
        don't want have to draw this one again.
    :param hang: Hang on the plot (wait for it to be closed before continuing)
    :param title: Title of the plot (will default to name if not included)
    :param fig: Name of the figure - use this when you want to create multiple figures.
    """
    if isinstance(fig, plt.Figure):
        assert None not in _DBPLOT_FIGURES, "If you pass a figure, you can only do it on the first call to dbplot (for now)"
        _DBPLOT_FIGURES[None] = fig
        fig = None
    elif fig not in _DBPLOT_FIGURES:
        _DBPLOT_FIGURES[fig] = _PlotWindow(figure = _make_dbplot_figure(), subplots=OrderedDict())
        if name is not None:
            _DBPLOT_FIGURES[fig].figure.canvas.set_window_title(fig)

    suplot_dict = _DBPLOT_FIGURES[fig].subplots

    if name not in suplot_dict:
        if isinstance(plot_constructor, str):
            plot = {
                'line': LinePlot,
                'pos_line': lambda: LinePlot(y_bounds=(0, None), y_bound_extend=(0, 0.05)),
                # 'pos_line': lambda: LinePlot(y_bounds=(0, None)),
                'img': ImagePlot,
                'colour': lambda: ImagePlot(is_colour_data=True),
                'equal_aspect': lambda: ImagePlot(aspect='equal'),
                'image_history': lambda: MovingImagePlot(),
                'pic': lambda: ImagePlot(show_clims=False, aspect='equal'),
                'notice': lambda: TextPlot(max_history=1, horizontal_alignment='center', vertical_alignment='center', size='x-large'),
                'cost': lambda: MovingPointPlot(y_bounds=(0, None), y_bound_extend=(0, 0.05)),
                'percent': lambda: MovingPointPlot(y_bounds=(0, 100)),
                'trajectory': lambda: Moving2DPointPlot(),
                'histogram': lambda: HistogramPlot()
                }[plot_constructor]()
        elif plot_constructor is None:
            plot = get_plot_from_data(data, mode=plot_mode)
        else:
            assert hasattr(plot_constructor, "__call__")
            plot = plot_constructor()

        _extend_subplots(fig=fig, subplot_name=name, plot_object=plot)  # This guarantees that the new plot will exist
        if xlabel is not None:
            _DBPLOT_FIGURES[fig].subplots[name].axis.set_xlabel(xlabel)
        if ylabel is not None:
            _DBPLOT_FIGURES[fig].subplots[name].axis.set_ylabel(ylabel)

    # Update the relevant data and plot it.  TODO: Add option for plotting update interval
    plot = _DBPLOT_FIGURES[fig].subplots[name].plot_object
    plot.update(data)
    if title is not None:
        _DBPLOT_FIGURES[fig].subplots[name].axis.set_title(title)

    plot.plot()
    plt.figure(_DBPLOT_FIGURES[fig].figure.number)
    if draw_now:
        if hang:
            plt.show()
        else:

            # Slow way:  ~6.6 FPS in demo_dbplot
            # plt.draw()
            # plt.pause(0.00001)

            # Faster way:  ~ 10.5 FPS
            # _DBPLOT_FIGURES[fig].figure.canvas.draw()
            # plt.show(block=False)
            #
            # Superfast way ~22.3 FPS
            # global _has_drawn
            if fig in _has_drawn:
                # See https://www.google.nl/search?q=speeding+up+matplotlib&gws_rd=cr&ei=DsD0V9-eGs6ba_jAtaAF
                # for how we could do more of this
                _DBPLOT_FIGURES[fig].figure.canvas.draw()
                _has_drawn.add(fig)
            else:
                _DBPLOT_FIGURES[fig].figure.canvas.flush_events()
            plt.show(block=False)
    return _DBPLOT_FIGURES[fig].subplots[name].axis

_has_drawn = set()  # Todo: record per-figure


def clear_dbplot(fig = None):
    plt.figure(_DBPLOT_FIGURES[fig].figure.number)
    plt.clf()
    _DBPLOT_FIGURES[fig].subplots.clear()


def _extend_subplots(fig, subplot_name, plot_object):
    """
    :param fig: Name for figure to extend subplots on
    :param subplot_name: Name of the new subplot in that figure
    :param plot_object: The plotting object to display
    :return:
    """
    assert fig in _DBPLOT_FIGURES
    old_key_names = _DBPLOT_FIGURES[fig].subplots.keys()
    plt.figure(_DBPLOT_FIGURES[fig].figure.number)
    n_rows, n_cols = vector_length_to_tile_dims(len(old_key_names)+1)
    gs = gridspec.GridSpec(n_rows, n_cols)
    for g, k in zip(gs, old_key_names):  # (gs can be longer but zip will just go to old_key_names)
        ax = _DBPLOT_FIGURES[fig].subplots[k].axis
        ax.set_position(g.get_position(_DBPLOT_FIGURES[fig].figure))

    # Add the new plot
    ax=_DBPLOT_FIGURES[fig].figure.add_subplot(gs[len(old_key_names)])
    ax.set_title(subplot_name)
    _DBPLOT_FIGURES[fig].subplots[subplot_name] = _Subplot(axis=ax, plot_object=plot_object)
