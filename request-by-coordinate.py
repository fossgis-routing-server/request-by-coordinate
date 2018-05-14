import cherrypy
import urllib.parse, urllib.request

"""
Dispatches OSRM routing requests to backend servers
depending on the requested start and end coordinates

This is a workaround because OSRM needs large amounts of
memory for preprocessing and running. This allows to
split it in parts and still offer worldwide routing
with the exception of routes across server boundaries.
"""

class RequestByCoordinate(object):

    def url2coordinates(self, url):

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
        coords = self.url2coordinates(query[-1])
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
                for server, sdata in servers.items():
                    poly = sdata[1]
                    if poly is not None and self.contains(poly, coord):
                        inside[server] += 1
                        nonefound = False
                        break
                if nonefound:
                    inside[defaultserver] += 1
            useserver = max(inside, key=inside.get)
        useserver = servers[useserver][0]

        requesturl = useserver + query[-1] + '?' + urllib.parse.urlencode(kwargs)
        try:
            response = urllib.request.urlopen(requesturl)
        except urllib.error.HTTPError as e:
            cherrypy.response.status = e.code
            response = e
        fetchedheaders = response.info()
        for i in cherrypy.response.headers.keys():
            if i not in fetchedheaders:
                del cherrypy.response.headers[i]
        for i in fetchedheaders:
            cherrypy.response.headers[i] = fetchedheaders[i]
        return response


if __name__ == '__main__':
    cherrypy.quickstart(RequestByCoordinate(), "/", "settings.cfg")
