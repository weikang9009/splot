""" 
Leightweight interactive visualizations in Bokeh.

TODO: 
"""

__author__ = ("Stefanie Lumnitz <stefanie.lumitz@gmail.com>")

import pandas as pd
import pysal as ps
import esda
from bokeh.plotting import figure
from bokeh.models import (GeoJSONDataSource, ColumnDataSource,
                          CategoricalColorMapper, Span,
                          HoverTool)
from bokeh.layouts import gridplot
from bokeh import palettes 

from ._viz_utils import (bin_labels_choropleth, add_legend,
                         mask_local_auto)


def plot_choropleth(df, attribute, title=None, plot_width=500,
                        plot_height=500, method='quantiles',
                        k=5, reverse_colors=False, tools=''):
    '''
    Plot Choropleth colored according to attribute
    
    Parameters
    ----------
    df : Geopandas dataframe
        Dataframe containign relevant shapes and attribute values.
    attribute : str
        Name of column containing attribute values of interest.
    title : str, optional
        Title of map. Default title=None
    plot_width : int, optional
        Width dimension of the figure in screen units/ pixels.
        Default = 500
    plot_height : int, optional
        Height dimension of the figure in screen units/ pixels.
        Default = 500
    method : str, optional
        Classification method to be used. Options supported:
        * 'quantiles' (default)
        * 'fisher-jenks'
        * 'equal-interval'
    k : int, optional
        Number of bins, assigning values to. Default k=5
    reverse_colors: boolean
        Reverses the color palette to show lightest colors for
        lowest values. Default reverse_colors=False
    
    Returns
    -------
    fig : Bokeh Figure instance
        Figure of Choropleth
    
    Examples
    --------
    >>> import libpysal.api as lp
    >>> from libpysal import examples
    >>> import geopandas as gpd
    >>> import esda
    >>> from splot.bk import plot_choropleth
    >>> from bokeh.io import show

    >>> link = examples.get_path('columbus.shp')
    >>> df = gpd.read_file(link)
    >>> w = lp.Queen.from_dataframe(df)
    >>> w.transform = 'r'

    >>> TOOLS = "tap,help"
    >>> fig = plot_choropleth(df, 'HOVAL', title='columbus',
    ...                       reverse_colors=True, tools=TOOLS)
    >>> show(fig) 
    '''
    # We're adding columns, do that on a copy rather than on the users' input
    df = df.copy()
    
    # Extract attribute values from df
    attribute_values = df[attribute].values
    
    # Create bin labels with bin_labels_choropleth()
    bin_labels = bin_labels_choropleth(df, attribute_values, method, k)
    
    # Initialize GeoJSONDataSource
    geo_source = GeoJSONDataSource(geojson=df.to_json())

    fig = _plot_choropleth_fig(geo_source, attribute, bin_labels, region_column=region_column,
                               title=title, plot_width=plot_width, plot_height=plot_height,
                               method=method, k=k, reverse_colors=reverse_colors, tools=tools)
    return fig


def _plot_choropleth_fig(geo_source, attribute, bin_labels, region_column='', title=None,
                         plot_width=500, plot_height=500, method='quantiles',
                         k=5, reverse_colors=False, tools=''):
    colors = palettes.Blues[k]
    if reverse_colors is True:
        colors.reverse()  # lightest color for lowest values

    # Create figure
    fig = figure(title=title, plot_width=plot_width, plot_height=plot_height, tools=tools)
    fig.patches('xs', 'ys', fill_alpha=0.7, 
              fill_color={'field': 'labels_choro',
                          'transform': CategoricalColorMapper(palette=colors,
                                                              factors=bin_labels)},
              line_color='white', line_width=0.5, source=geo_source)

    # add hover tool
    if 'hover' in tools:
        hover = fig.select_one(HoverTool)
        hover.point_policy = "follow_mouse"
        hover.tooltips = [
        ("Region", "@" + region_column),
        ("Attribute", "@" + attribute + "{0.0}"),
        ]
    
    # add legend with add_legend()
    add_legend(fig, bin_labels, colors)
    
    # change layout
    fig.xgrid.grid_line_color = None
    fig.ygrid.grid_line_color = None
    fig.axis.visible = None
    return fig


def lisa_cluster(moran_loc, df, p=0.05, region_column='', title=None, plot_width=500,
                     plot_height=500, tools=''): 
    '''
    Lisa Cluster map, coloured by local spatial autocorrelation
    
    Parameters
    ----------
    moran_loc : esda.moran.Moran_Local instance
        values of Moran's Local Autocorrelation Statistic
    df : geopandas dataframe instance
        In mask_local_auto(), assign df['labels'] per row. Note that 
        ``df`` will be modified, so calling functions uses a copy of
        the user provided ``df``.
    p : float, optional
        The p-value threshold for significance. Points will
        be colored by significance.
    title : str, optional
        Title of map. Default title=None
    plot_width : int, optional
        Width dimension of the figure in screen units/ pixels.
        Default = 500
    plot_height : int, optional
        Height dimension of the figure in screen units/ pixels.
        Default = 500
    
    Returns
    -------
    fig : Bokeh figure instance
        Figure of LISA cluster map, colored by local spatial autocorrelation

    Examples
    --------
    >>> import libpysal.api as lp
    >>> from libpysal import examples
    >>> import geopandas as gpd
    >>> import esda
    >>> from splot.bk import lisa_cluster
    >>> from bokeh.io import show

    >>> link = examples.get_path('columbus.shp')
    >>> df = gpd.read_file(link)
    >>> y = df['HOVAL'].values
    >>> w = lp.Queen.from_dataframe(df)
    >>> w.transform = 'r'
    >>> moran_loc = esda.moran.Moran_Local(y, w)

    >>> TOOLS = "tap,reset,help"
    >>> fig = lisa_cluster(moran_loc, df, p=0.05, tools=TOOLS)
    >>> show(fig)
    '''
    # We're adding columns, do that on a copy rather than on the users' input
    df = df.copy()
    
    # add cluster_labels and colors5 in mask_local_auto
    cluster_labels, colors5, _, _ = mask_local_auto(moran_loc, df=df, p=0.05)
    df['moranloc_psim'] = moran_loc.p_sim
    df['moranloc_q'] = moran_loc.q

    # load df into bokeh data source
    geo_source = GeoJSONDataSource(geojson=df.to_json())

    fig = _lisa_cluster_fig(geo_source, moran_loc, cluster_labels, colors5, region_column=region_column, title=title, plot_width=plot_width,
                            plot_height=plot_height, tools=tools)

    return fig


def _lisa_cluster_fig(geo_source, moran_loc, cluster_labels, colors5, region_column='', title=None, plot_width=500,
                      plot_height=500, tools=''): 
    # Create figure
    fig = figure(title=title, toolbar_location='right',
          plot_width=plot_width, plot_height=plot_height, tools=tools)
    fig.patches('xs', 'ys', fill_alpha=0.8, 
              fill_color={'field': 'labels_lisa',
                          'transform': CategoricalColorMapper(palette=colors5,
                                                              factors=cluster_labels)}, 
              line_color='white', line_width=0.5, source=geo_source)
    
    if 'hover' in tools:
        # add hover tool
        hover = fig.select_one(HoverTool)
        hover.point_policy = "follow_mouse"
        hover.tooltips = [
        ("Region", "@" + region_column),
        ("Significance", "@moranloc_psim{0.00}"),
        ("Quadrant", "@moranloc_q{0}")
        ]

    # add legend with add_legend()
    add_legend(fig, cluster_labels, colors5)
    
    # change layout
    fig.xgrid.grid_line_color = None
    fig.ygrid.grid_line_color = None
    fig.axis.visible = None

    return fig


def mplot(moran_loc, p=None, region_column='', plot_width=500, plot_height=500, tools=''): 
    '''
    Moran Scatterplot, optional coloured by local spatial autocorrelation
    
    Parameters
    ----------
    moran_loc : esda.moran.Moran_Local instance
        values of Moran's Local Autocorrelation Statistic
    p : float, optional
        The p-value threshold for significance. Points will
        be colored by significance.
    plot_width : int, optional
        Width dimension of the figure in screen units/ pixels.
        Default = 500
    plot_height : int, optional
        Height dimension of the figure in screen units/ pixels.
        Default = 500
    
    Returns
    -------
    fig : Bokeh figure instance
        Figure of Moran Scatterplot, optionally colored by
        local spatial autocorrelation

    Examples
    --------
    >>> import libpysal.api as lp
    >>> from libpysal import examples
    >>> import geopandas as gpd
    >>> import esda
    >>> from splot.bk import mplot
    >>> from bokeh.io import show

    >>> link = examples.get_path('columbus.shp')
    >>> df = gpd.read_file(link)
    >>> y = df['HOVAL'].values
    >>> w = lp.Queen.from_dataframe(df)
    >>> w.transform = 'r'
    >>> moran_loc = esda.moran.Moran_Local(y, w)

    >>> fig = mplot(moran_loc, p=0.05)
    >>> show(fig)
    '''   
    data = _mplot_calc(moran_loc, p)
    source = ColumnDataSource(pd.DataFrame(data))
    fig = _mplot_fig(source, p=p, region_column=region_column, plot_width=plot_width,
                     plot_height=plot_height, tools=tools)
    return fig


def _mplot_calc(moran_loc, p):
    lag = ps.lag_spatial(moran_loc.w, moran_loc.z)
    fit = ps.spreg.OLS(moran_loc.z[:, None], lag[:,None])
    if p is not None:
        if not isinstance(moran_loc, esda.moran.Moran_Local):
            raise ValueError("`moran_loc` is not a Moran_Local instance")
    
        _, _, colors, _ = mask_local_auto(moran_loc, p=p)
    else:
        colors = 'black'

    data = {'moran_z': moran_loc.z, 'lag': lag,
            'colors': colors, 'fit_y': fit.predy.flatten(),
            'moranloc_psim': moran_loc.p_sim, 'moranloc_q': moran_loc.q}
    return data


def _mplot_fig(source, p=None, region_column='', plot_width=500, plot_height=500, tools=''):
    """
    
    Parameters
    ----------
    source : Bokeh ColumnDatasource or GeoJSONDataSource instance
        The data source, should contain the columns ``moran_z`` and ``lag``,
        which will be used as x and y inputs of the scatterplot.

    """
    # Vertical line
    vline = Span(location=0, dimension='height', line_color='lightskyblue', line_width=2, line_dash = 'dashed')
    # Horizontal line
    hline = Span(location=0, dimension='width', line_color='lightskyblue', line_width=2, line_dash = 'dashed')
    
    # Create figure
    fig = figure(title="Moran Scatterplot", x_axis_label='Response', y_axis_label='Spatial Lag',
                 toolbar_location='left', plot_width=plot_width, plot_height=plot_height, tools=tools)
    fig.scatter(x='moran_z', y='lag', source=source, color='colors', size=8, fill_alpha=.6)
    fig.renderers.extend([vline, hline])
    fig.xgrid.grid_line_color = None
    fig.ygrid.grid_line_color = None
    fig.line(x='lag', y='fit_y', source=source, line_width=2) # fit line

    if 'hover' in tools:
        hover = fig.select_one(HoverTool)
        hover.point_policy = "follow_mouse"
        hover.tooltips = [
        ("Region", "@" + region_column),
        ("Significance", "@moranloc_psim{0.00}"),
        ("Quadrant", "@moranloc_q{0}")
        ]
    return fig


def plot_local_autocorrelation(moran_loc, df, attribute, p=0.05, region_column='', plot_width=250,
                               plot_height=300, method='quantiles', k=5,
                               reverse_colors=False):
    """
    Plot Moran Scatterplot, LISA cluster and Choropleth
    for Local Spatial Autocorrelation Analysis
    
    Parameters
    ----------
    moran_loc : esda.moran.Moran_Local instance
        values of Moran's Local Autocorrelation Statistic
    df : Geopandas dataframe
        Dataframe containing relevant polygon and attribute values.
    attribute : str
        Name of column containing attribute values of interest.
    plot_width : int, optional
        Width dimension of the figure in screen units/ pixels.
        Default = 250
    plot_height : int, optional
        Height dimension of the figure in screen units/ pixels.
        Default = 300
    method : str, optional
        Classification method to be used. Options supported:
        * 'quantiles' (default)
        * 'fisher-jenks'
        * 'equal-interval'
    k : int, optional
        Number of bins, assigning values to. Default k=5
    reverse_colors: boolean
        Reverses the color palette to show lightest colors for
        lowest values in Choropleth map. Default reverse_colors=False
    
    Returns
    -------
    fig : Bokeh Figure instance
        Figure of Choropleth

    Examples
    --------
    >>> import libpysal.api as lp
    >>> from libpysal import examples
    >>> import geopandas as gpd
    >>> import esda
    >>> from splot.bk import plot_local_autocorrelation
    >>> from bokeh.io import show

    >>> link = examples.get_path('columbus.shp')
    >>> df = gpd.read_file(link)
    >>> y = df['HOVAL'].values
    >>> w = lp.Queen.from_dataframe(df)
    >>> w.transform = 'r'
    >>> moran_loc = esda.moran.Moran_Local(y, w)

    >>> fig = plot_local_autocorrelation(moran_loc, df, 'HOVAL', reverse_colors=True)
    >>> show(fig) 
    """
    #DEBUG: import IPython; IPython.embed()
    # We're adding columns, do that on a copy rather than on the users' input
    df = df.copy()
    
    # Add relevant results for mplot as columns to geodataframe
    mplot_data = _mplot_calc(moran_loc, p)
    for key in mplot_data:
        df[key] = mplot_data[key]

    # add cluster_labels and colors5 in mask_local_auto
    cluster_labels, colors5, _, _ = mask_local_auto(moran_loc, df=df, p=0.05)
    df['moranloc_psim'] = moran_loc.p_sim
    df['moranloc_q'] = moran_loc.q
    # Extract attribute values from df
    attribute_values = df[attribute].values
    # Create bin labels with bin_labels_choropleth()
    bin_labels = bin_labels_choropleth(df, attribute_values, method, k)

    # load df into bokeh data source
    geo_source = GeoJSONDataSource(geojson=df.to_json())

    TOOLS = "tap,reset,help,hover"
    
    #scatter = mplot(moran_loc, p=p, plot_width=plot_width, plot_height=plot_height, tools=TOOLS)
    scatter = _mplot_fig(geo_source, p=p, region_column=region_column, plot_width=plot_width, plot_height=plot_height,
                         tools=TOOLS)
    LISA = _lisa_cluster_fig(geo_source, moran_loc, cluster_labels, colors5, region_column=region_column, plot_width=plot_width,
                             plot_height=plot_height, tools=TOOLS)
    choro = _plot_choropleth_fig(geo_source, attribute, bin_labels, region_column=region_column, reverse_colors=reverse_colors,
                                 plot_width=plot_width, plot_height=plot_height,
                                 tools=TOOLS)
    
    fig = gridplot([[scatter, LISA, choro]],
                   sizing_mode='fixed')
    return fig
