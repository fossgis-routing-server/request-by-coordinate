# request-by-coordinate

Dispatches OSRM routing requests to backend servers
depending on the requested start and end coordinates

You can directly start request-by-coordinate.py to run a local server with cherrypy.

## configuration

* `modes` lets you define which routing profiles are supported.
* each mode gets its own section in the config file
  * `servers` contains a list of regions
  * for each region define `url_*` and `polygon_*` (`*` denotes the name of the region)
  * One region should be the default which is a `None` polygon
  * `polygon_*` is a list of coordinates, each coordinate is a list of two numbers

Example:

    [modes]
    modes: ["car"]
    
    [car]
    servers: ["am", "eu"]
    url_am: "http://routing.server/car-region-am/route/v1/driving/"
    url_eu: "http://routing.server/car-region-eu/route/v1/driving/"
    polygon_am: None
    polygon_eu: [[-1.09898437500, 90], [-12.52476562500, 71.10265660445], [-35.02476562500, 62.06289796703], [-46.80210937500, 17.05712070850], [-30.45445312500, -3.07434401590], [0.83460937500, -90], [180, -90], [180, 90], [-1.09898437500, 90]]

## Example request forwarding

With the above config file, if the request is

    http://127.0.0.1:8080/car/route/v1/driving/-77.02360153198242,38.90212168702489;-76.99270248413086,38.89330417988778?overview=false&alternatives=true&steps=true

the script will request 

    http://routing.server/car-region-am/route/v1/driving/-77.02360153198242,38.90212168702489;-76.99270248413086,38.89330417988778?overview=false&alternatives=true&steps=true
and forward the result
