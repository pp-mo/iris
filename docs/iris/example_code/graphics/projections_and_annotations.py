"""
Plotting in different projections
=================================

This example shows how to overlay data and graphics in different projections,
demonstrating various features of Iris, Cartopy and matplotlib.

We wish to overlay two datasets, defined on different rotated-pole grids.
To display both datasets together, we make a color blockplot of the first,
overlaid with contour lines from the second.

We plot these over a specified region, for two different map projections.
We also add some lines and text annotations described in different projections.

"""
import cartopy.crs as ccrs
import iris
import iris.plot as iplt
import numpy as np
import matplotlib.pyplot as plt


def make_plot(projection_name, plot_projection_crs, plot_region_limits):
    # Create a matplotlib Figure.
    fig = plt.figure()
    # Create a matplotlib Axes, specifying the required display projection.
    # NOTE: specifying 'projection' (a "cartopy.crs.Projection") makes the
    # result a "cartopy.mpl.geoaxes.GeoAxes", which supports plotting in
    # different coordinate systems.
    ax = plt.axes(projection=plot_projection_crs)

    # Set the displayed region (display coordinate values).
    ax.set_xlim(plot_region_limits[:2])
    ax.set_ylim(plot_region_limits[2:])
    # Add coastlines for orientation.
    ax.coastlines(linewidth=0.75, color='maroon')

    # Plot first dataset as a block-plot.
    data_1_filepath = iris.sample_data_path('rotated_pole.nc')
    datacube_1 = iris.load_cube(data_1_filepath)
    # NOTE: iplt.pcolormesh calls "pyplot.pcolormesh", but specifying a data
    # coordinate system with the 'transform' keyword:  This enables the Axes
    # (a cartopy GeoAxes) to reproject the plot into the display projection.
    iplt.pcolormesh(datacube_1)

    # Overplot the other dataset (on a different projection grid), as contours.
    data_2_filepath = iris.sample_data_path('space_weather.nc')
    datacube_2 = iris.load_cube(data_2_filepath, 'total electron content')
    # NOTE: as above, "iris.plot.contour" calls "pyplot.contour" with a
    # 'transform' keyword, enabling Cartopy reprojection.
    iplt.contour(datacube_2, 20, linewidths=2.5, colors='blue', linestyles='-')

    # Draw a margin line, some way in from the border of 'datacube_1'...
    # First calculate box corners, 7% in from each corner of the data.
    coord_x1, coord_y1 = datacube_1.coord(axis='x'), datacube_1.coord(axis='y')
    x0, x1 = np.min(coord_x1.points), np.max(coord_x1.points)
    y0, y1 = np.min(coord_y1.points), np.max(coord_y1.points)
    f0, f1 = 0.07, 0.93
    box_x_pts = x0 + (x1 - x0) * np.array([f0, f1, f1, f0, f0])
    box_y_pts = y0 + (y1 - y0) * np.array([f0, f0, f1, f1, f0])
    # Extract the coordinate sytem of 'datacube_1'.
    crs_data1 = coord_x1.coord_system.as_cartopy_crs()
    # Draw a box outline, with matplotlib "pyplot.plot".
    # NOTE: the 'transform' keyword specifies a non-display coordinate system
    # for plotting coordinates (as used by the "iris.plot" functions).
    plt.plot(box_x_pts, box_y_pts, transform=crs_data1,
             linewidth=2.0, color='white', linestyle='--')

    # Mark some particular places with a small circle and a name label...
    # Define some test points with coords in lat-lon.
    city_data = [('London', 51.5072, 0.1275),
                 ('Halifax, NS', 44.67, -63.61),
                 ('Reykjavik', 64.1333, -21.9333)]
    # Define an 'ordinary' lat-lon projection.
    crs_pc = ccrs.PlateCarree()
    # Annotate each place.
    for name, lat, lon in city_data:
        plt.plot(lon, lat, marker='o', markersize=7.0, color='white',
                 transform=crs_pc)
        # NOTE: the "plt.annotate call" does not have a "transform=" keyword,
        # so for this we transform the coordinates with a Cartopy call.
        at_x, at_y = ax.projection.transform_point(lon, lat, src_crs=crs_pc)
        plt.annotate(
            name, xy=(at_x, at_y), xytext=(30, 20), textcoords='offset points',
            color='black', size='large', weight='bold',
            arrowprops=dict(arrowstyle='->', color='black', linewidth=2.5))

    # Add a title, and display.
    plt.title('A block-plot on the {} projection,\n'
              'with overlaid contours.'.format(projection_name))
    plt.show()


def main():
    # Demonstrate with suitable settings for 2 different display projections.
    make_plot('Equidistant Cylindrical', ccrs.PlateCarree(),
              (-80.0, 20.0, 20.0, 80.0))
    make_plot('North Polar Stereographic', ccrs.NorthPolarStereo(),
              (-7.4e6, 4.2e6, -7.7e6, -0.5e6))


if __name__ == '__main__':
    main()
