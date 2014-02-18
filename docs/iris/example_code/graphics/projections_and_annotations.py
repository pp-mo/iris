"""
Plotting in a different projection
==================================

This example shows how to overlay data and graphics in different projections,
demonstrating various features of Iris, Cartopy and matplotlib.

We wish to overlay two datasets, defined on different rotated-pole grids.
We plot these over a specified region of a standard latitude-longitude map.
To display both together, we make a color blockplot of the first dataset,
overlaid with contour lines from the other one.  We also add some lines and
text annotations described in different projections.

"""
import cartopy.crs as ccrs
import iris
import iris.plot as iplt
import numpy as np
import matplotlib.pyplot as plt


def main():
    # Create a matplotlib Figure.
    fig = plt.figure()
    # Create a matplotlib Axes, specifying the PlateCarree projection.
    # NOTE: specifying 'projection' (a "cartopy.crs.Projection") makes the
    # result a "cartopy.mpl.geoaxes.GeoAxes", which supports plotting in
    # different coordinate systems.
    ax = plt.axes(projection=ccrs.PlateCarree())

    # Setup map display (all Cartopy-specific, not ordinary Axes features)...
    # Set the displayed region (in PlateCarree coordinates, i.e. lat-lon).
    ax.set_extent((-80.0, 20.0, 20.0, 80.0))
    # Add coastlines and some labelled gridlines, for orientation.
    ax.coastlines(linewidth=0.75, color='maroon')
    gl = ax.gridlines(draw_labels=True)
    # Remove top gridlabels (just to avoid collision with the plot title).
    gl.xlabels_top = False

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

    # Draw a margin line, some way in from the border of 'data_1'...
    # First calculate box corners, 7% in from each corner of the data.
    coord_x1, coord_y1 = datacube_1.coord(axis='x'), datacube_1.coord(axis='y')
    x0, x1 = np.min(coord_x1.points), np.max(coord_x1.points)
    y0, y1 = np.min(coord_y1.points), np.max(coord_y1.points)
    f0, f1 = 0.07, 0.93
    box_x_pts = x0 + (x1 - x0) * np.array([f0, f1, f1, f0, f0])
    box_y_pts = y0 + (y1 - y0) * np.array([f0, f0, f1, f1, f0])
    # Draw a box outline, with matplotlib "pyplot.plot".
    crs_rot = coord_x1.coord_system.as_cartopy_crs()
    # NOTE: the 'transform' keyword specifies the non-display coordinate system
    # for the plot coordinates (as used by the "iris.plot" functions).
    plt.plot(box_x_pts, box_y_pts, transform=crs_rot,
             linewidth=2.0, color='white', linestyle='--')

    # Mark some particular places with a small circle and a name label.
    city_data = [('London', 51.5072, 0.1275),
                 ('Halifax, NS', 44.67, -63.61),
                 ('Reykjavik', 64.1333, -21.9333)]
    for name, lat, lon in city_data:
        # NOTE: "transform=" is not needed in either call here, as 'lat' and
        # 'lon' values are already in display coordinates.
        plt.plot(lon, lat, marker='o', markersize=7.0, color='white')
        plt.annotate(
            name, xy=(lon, lat), xytext=(lon+10, lat+5),
            color='black', size='large', weight='bold',
            arrowprops=dict(arrowstyle='->', color='black', linewidth=2.5))

    # Add a title, and display.
    plt.title('A projected block-plot, with overlaid contours.')
    plt.show()


if __name__ == '__main__':
    main()
