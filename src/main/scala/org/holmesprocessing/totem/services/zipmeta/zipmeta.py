# imports for tornado
import tornado
from tornado import web, httpserver, ioloop

# imports for logging
import traceback
import os
from os import path

# imports for zipmeta
import ZipParser
ZipParser = ZipParser.ZipParser

# imports for largefile reader
from holmeslibrary.files    import LargeFileReader

import json

# Reading configuration file
def ServiceConfig(filename):
    configPath = filename
    try:
        return json.loads(open(configPath).read())
    except FileNotFoundError:
        raise tornado.web.HTTPError(500)

# Get service meta information and configuration
Config = ServiceConfig("./service.conf")

Metadata = {
    "Name"        : "ZipMeta",
    "Version"     : "1.0",
    "Description" : "./README.md",
    "Copyright"   : "Copyright 2016 Holmes Group LLC",
    "License"     : "./LICENSE"
}


# class ZipError (ServiceRequestError):
    # pass

class ZipMetaProcess(tornado.web.RequestHandler):
    def get(self):
        # resultset = ServiceResultSet()
        resultset = {}
        try:
            filename = self.get_argument("obj", strip=False)
            # read file
            fullPath = os.path.join('/tmp/', filename)
            data     = LargeFileReader(fullPath) # create virtual memory map
            # exclude non-zip
            if len(data) < 4:
                raise ZipError(400, "Not enough filedata.")

            if data[:4].decode('UTF-8') not in [ZipParser.zipLDMagic, ZipParser.zipCDMagic]:
                raise ZipError(400, "Not a zip file.")

            # parse
            parser    = ZipParser(data)

            parsedZip = parser.parseZipFile()
            if not parsedZip:
                raise ZipError(400, "Could not parse file as a zip file")

            # clean up
            data.close()

            # fetch result
            resultset["filecount"] = len(parsedZip)
            for centralDirectory in parsedZip:
                zipfilename = centralDirectory["ZipFileName"]
                zipentry = {}

                # for name, value in centralDirectory.iteritems():
                for name, value in centralDirectory.items():
                    if name == 'ZipExtraField':
                        continue

                    if type(value) is list or type(value) is tuple:
                        for element in value:
                            zipentry[name]=str(element)

                    else:
                        zipentry[name] = str(value)

                if centralDirectory["ZipExtraField"]:
                    for dictionary in centralDirectory["ZipExtraField"]:
                        zipextra = {}
                        if dictionary["Name"] == "UnknownHeader":
                            for name, value in dictionary.items():
                                if name == "Data":
                                    value = "Data"
                                zipextra[name] = str(value)
                        else:
                            for name, value in dictionary.items():
                                zipextra[name]=str(value)
                else:
                    zipentry["ZipExtraField"] = "None"

                resultset[zipfilename]= {**zipentry, **zipextra}

            self.write(resultset)
        except tornado.web.MissingArgumentError:
            raise tornado.web.HTTPError(400)
        except ZipError as ze:
            self.set_status(ze.status, str(ze.error))
            self.write("")
        except Exception as e:
            self.set_status(500, str(e))
            self.write({"error": traceback.format_exc(e)})


class Info(tornado.web.RequestHandler):
    # Emits a string which describes the purpose of the analytics
    def get(self):
        info = """
            <p>{name:s} - {version:s}</p>
            <hr>
            <p>{description:s}</p>
            <hr>
            <p>{license:s}
        """.format(
            name        = str(Metadata["Name"]).replace("\n", "<br>"),
            version     = str(Metadata["Version"]).replace("\n", "<br>"),
            description = str(Metadata["Description"]).replace("\n", "<br>"),
            license     = str(Metadata["License"]).replace("\n", "<br>")
        )
        self.write(info)


class ZipMetaApp(tornado.web.Application):
    def __init__(self):

        for key in ["Description", "License"]:
            fpath = Metadata[key]
            if os.path.isfile(fpath):
                with open(fpath) as file:
                    Metadata[key] = file.read()

        handlers = [
            (r'/', Info),
            (r'/analyze/', ZipMetaProcess),
        ]
        settings = dict(
            template_path=path.join(path.dirname(__file__), 'templates'),
            static_path=path.join(path.dirname(__file__), 'static'),
        )
        tornado.web.Application.__init__(self, handlers, **settings)
        self.engine = None


def main():
    server = tornado.httpserver.HTTPServer(ZipMetaApp())
    server.listen(Config["settings"]["httpbinding"])
    try:
        tornado.ioloop.IOLoop.current().start()
    except KeyboardInterrupt:
        tornado.ioloop.IOLoop.current().stop()


if __name__ == '__main__':
    main()
