import cherrypy
import urllib.parse, urllib.request
import math
from polyline import decodePolyline

"""
Dispatches OSRM routing requests to backend servers
depending on the requested start and end coordinates

This is a workaround because OSRM needs large amounts of
memory for preprocessing and running. This allows to
split it in parts and still offer worldwide routing
with the exception of routes across server boundaries.
"""

def null_island():
    cherrypy.response.headers["Access-Control-Allow-Headers"] = "X-Requested-With, Content-Type"
    cherrypy.response.headers["Access-Control-Allow-Methods"] = "GET"
    cherrypy.response.headers["Access-Control-Allow-Origin"] = "*"
    cherrypy.response.headers["Content-Disposition"]= "inline; filename=\"response.json\""
    cherrypy.response.headers["Content-Type"] = "application/json; charset=UTF-8"
    return ('{"message":'
        + '"Welcome to Null Island. At least one point you entered is 0,0 (Which is in '
        + 'the middle of the ocean. There is only a buoy known as Null Island) which '
        + 'means that this query is not meaningful. Because this is so common, we '
        + 'don\'t answer requests for 0,0 to preserve resources.",'
        + '"code":"InvalidOptions"}').encode("UTF8")

def tile2upper_left_coordinate(z,x,y):
    s = float(2**z)
    lon = float(x) / s * 360. - 180.
    lat = math.atan(math.sinh(math.pi - float(y) / s * 2 * math.pi)) * 180 / math.pi
    return (lon, lat)

def tile2coordinates(tilestring):
    try:
        x, y, z = (int(i) for i in tilestring.split(','))
    except:
        return None
    return [tile2upper_left_coordinate(z, x, y),
            tile2upper_left_coordinate(z, x + 1, y + 1)]


def url2coordinates(url):

    try:
        coords = url.split(';')
    except:
        return None
    try:
        coords = [c.split(',') for c in coords]
    except:
        return None
    for c in coords:
        if len(c) != 2:
            return None
    try:
        coords = [(float(c[0]), float(c[1])) for c in coords]
    except:
        return None
    return coords

class RequestByCoordinate(object):

    def contains(self, poly, testpoint):
        c = False
        for i in range(len(poly)):
            v1 = poly[i]
            v2 = poly[i-1]
            if (v1[1] > testpoint[1]) != (v2[1] > testpoint[1]):
                if testpoint[0] < ((v2[0]-v1[0])
                        * (testpoint[1] - v1[1]) / (v2[1] - v1[1]) + v1[0]):
                    c = not c
        return c


    @cherrypy.expose
    def default(self, *query, **kwargs):
        if len(query) < 1:
            raise cherrypy.HTTPError(404)
        mode = query[0]
        if mode not in cherrypy.request.app.config["modes"]["modes"]:
            raise cherrypy.HTTPError(404)

        filepart = query[-1]

        if len(filepart) > 13 and filepart[:5] == "tile(":
            #debug tile requet
            coords = tile2coordinates(filepart[5:-5])
        elif filepart[:9] == "polyline(":
            #poly line encoded coordinates
            coords = decodePolyline(filepart[9:-1])
            if not all(map(lambda coord: coord[0] or coord[1], coords)):
                return null_island()
        else:
            #semicolon delimited coordinate pairs (lon,lat;...)
            coords = url2coordinates(filepart)
            if not all(map(lambda coord: coord[0] or coord[1], coords)):
                return null_island()

        serverset = cherrypy.request.app.config[mode]["servers"]
        servers = dict();
        defaultserver = next(iter(serverset))
        for server in serverset:
            poly = cherrypy.request.app.config[mode]["polygon_" + server]
            url = cherrypy.request.app.config[mode]["url_" + server]
            if poly is None:
                defaultserver = server
            servers[server] = (url, poly)
        useserver = defaultserver
        if coords is not None:
            inside = {k : 0 for k in servers}
            for coord in coords:
                nonefound = True
                for server, sdata in list(servers.items()):
                    poly = sdata[1]
                    if poly is not None and self.contains(poly, coord):
                        inside[server] += 1
                        nonefound = False
                        break
                if nonefound:
                    inside[defaultserver] += 1
            useserver = max(inside, key=inside.get)
        useserver = servers[useserver][0]

        requesturl = useserver + '/' + '/'.join(query[1:])
        if cherrypy.request.query_string:
            requesturl += '?' + cherrypy.request.query_string
        try:
            response = urllib.request.urlopen(requesturl)
        except urllib.error.HTTPError as e:
            cherrypy.response.status = e.code
            response = e
        except:
            raise cherrypy.HTTPError(500, "Routing backend is not reachable")
        fetchedheaders = response.info()
        for i in list(cherrypy.response.headers.keys()):
            if i not in fetchedheaders:
                del cherrypy.response.headers[i]
        for i in fetchedheaders:
            cherrypy.response.headers[i] = fetchedheaders[i]
        return response


if __name__ == '__main__':
    cherrypy.quickstart(RequestByCoordinate(), "/", "settings.cfg")
else:
     # Setup WSGI stuff

    if cherrypy.__version__.startswith('3.0') and cherrypy.engine.state == 0:
        cherrypy.engine.start(blocking=False)
        atexit.register(cherrypy.engine.stop)

    cherrypy.config.update('settings.cfg')
    application = cherrypy.Application(RequestByCoordinate(), script_name=None,
                    config='settings.cfg')

