# Copyright (C) 2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

from XQuery import XQuery
import os, httplib, urlparse, base64
try:
    from lxml import etree
except ImportError:
    have_lxml = False
else:
    have_lxml = True

class ExistDB(object):
    """
    The eXist-db connection object.
    """
    RESULT_NS = 'http://exist.sourceforge.net/NS/exist'

    class Error(Exception):
        pass

    def __init__(self, host_uri, collection = '', query_cls = XQuery):
        """
        Create a new database connection using the REST protocol.

        @type  host_uri: string
        @param host_uri: The host and port number, separated by a ':' character.
        @type  collection: string
        @param collection: A database (collection) name.
        """
        # Python's urlparse module is so bad it hurts.
        uri = urlparse.urlparse('http://' + host_uri)
        try:
            auth, self.netloc = uri.netloc.split('@', 1)
        except ValueError:
            auth        = ''
            self.netloc = uri.netloc
        self.username   = auth.split(':', 1)[0]
        self.password   = auth[len(self.username) + 1:]
        self.collection = collection
        self.path       = ''
        if uri.path:
            self.path += '/' + uri.path.strip('/')
        if collection:
            self.path += '/' + collection.strip('/')
        self.query_cls = query_cls

    def _get_connection(self, method, path):
        conn = httplib.HTTP(self.netloc)
        conn.putrequest('PUT', path)
        if not self.username:
            return conn
        if self.password:
            auth = self.username + ':' + self.password
        else:
            auth = self.username
        auth = base64.encodestring(auth).strip()
        conn.putheader('Authorization', 'Basic ' + auth)
        return conn

    def store(self, docname, xml):
        """
        Imports the XML string into the document with the given name.

        @type  docname: string
        @param docname: Document name in database.
        @type  xml: string or lxml.ElementTree
        @param xml: XML document to import.
        """
        if have_lxml:
            try:
                xml = etree.tostring(xml, encoding='utf-8')
            except TypeError:
                pass

        conn = self._get_connection('PUT', self.path + '/' + docname)
        conn.putheader('Content-Type',   'text/xml')
        conn.putheader('Content-Length', str(len(xml)))
        conn.endheaders()
        conn.send(xml)

        errcode, errmsg, headers = conn.getreply()
        if errcode != 201:
            raise ExistDB.Error('Error %d: %s' % (errcode, errmsg))
        conn.close()

    def store_file(self, filename, docname = None):
        """
        Like store(), but reads the XML from a file instead. If the document
        name is None, it defaults to the basename of the file, with the .xml
        extension removed.

        @type  filename: string
        @param filename: The name of an XML file.
        @type  docname: string
        @param docname: A document name.
        """
        if docname is None:
            docname = os.path.splitext(os.path.basename(filename))[0]
        xml = open(filename).read()
        self.store(docname, xml)

    def delete(self, docname):
        """
        Deletes the document with the given name. Raises an error if the
        document does not exist.

        @type  docname: string
        @param docname: Document name in database.
        """
        conn = self._get_connection('DELETE', self.path + '/' + docname)
        conn.endheaders()

        errcode, errmsg, headers = conn.getreply()
        if errcode != 200:
            raise ExistDB.Error('Error %d: %s' % (errcode, errmsg))
        conn.close()

    def _post(self, thequery, start = 1, max = None):
        thequery = package_query(thequery)
        conn     = self._get_connection('POST', self.path)
        conn.putheader('Content-Type',   'text/xml')
        conn.putheader('Content-Length', str(len(thequery)))
        conn.endheaders()
        conn.send(thequery)

        errcode, errmsg, headers = conn.getreply()
        if errcode not in (200, 202):
            raise ExistDB.Error('Error %d: %s' % (errcode, errmsg))

        response = conn.getfile().read()
        conn.close()
        return response

    def query(self, thequery, **kwargs):
        """
        Creates a new query object from the given xquery statement.
        The given kwargs are parameters that are replaced in the query.
        The query may use the following syntax for such parameters::

            let myvar := '%{myparam}'

        Passing "myparam = 'foo'" will produce the following query::

            let myvar := 'foo'

        @type  thequery: string
        @param thequery: The xquery as a string.
        @type  kwargs: dict
        @param kwargs: Parameters to pass into the query.
        @rtype:  XQuery
        @return: An XQuery object.
        """
        return self.query_cls(self, thequery, **kwargs)

    def query_from_file(self, filename, **kwargs):
        """
        Like query(), but reads the xquery from the file with the given
        name instead.

        @type  filename: string
        @param filename: The name of a file containing the query.
        @type  kwargs: dict
        @param kwargs: Parameters to pass into the query.
        @rtype:  XQuery
        @return: An XQuery object.
        """
        thequery = open(filename, 'r').read()
        return self.query(thequery, **kwargs)

    def move(self, source, destination):
        """
        Moves the given source document to the given destination.
        Note that you can not rename a document and move it to another
        collection in the same call; this is a limitation of the XQuery
        API.

        @type  source: string
        @param source: Document name in database.
        @type  destination: string
        @param destination: A collection name in database.
        """
        xquery = '''
        let $status := xmldb:move('%{source}', '%{destination}', '%{resource}')
        return <status>{$status}</status>
        '''

        if self.collection and not source.startswith('/'):
            source = self.collection + '/' + source
        if self.collection and not destination.startswith('/'):
            destination = self.collection + '/' + destination
        try:
            sourcecol, sourceres = source.rsplit('/', 1)
        except ValueError:
            sourcecol = ''
            sourceres = source
        query = self.query(xquery,
                           source      = sourcecol,
                           resource    = sourceres,
                           destination = destination)
        query.execute()
        return query

    def rename(self, resource, new_name):
        """
        Renames the given document (without moving it).

        @type  resource: string
        @param resource: Document name in database.
        @type  new_name: string
        @param new_name: The new name.
        """
        xquery = '''
        let $status := xmldb:rename('%{collection}', '%{resource}', '%{newname}')
        return <status>{$status}</status>
        '''
        if self.collection and not resource.startswith('/'):
            resource = self.collection + '/' + resource
        try:
            collection, resource = resource.rsplit('/', 1)
        except ValueError:
            collection = ''
        query = self.query(xquery,
                           collection = collection,
                           resource   = resource,
                           newname    = new_name)
        query.execute()
        return query

    def copy(self, source, destination):
        """
        Copies the given source document to the given destination.

        @type  source: string
        @param source: Document or collection name in database.
        @type  destination: string
        @param destination: Collection name in database.
        """
        xquery = '''
        if (xmldb:collection-available('%{source}'))
        then
            (: The source is a collection name :)
            let $status := xmldb:copy('%{source}', '%{destination}')
            return <status>{$status}</status>
        else
            (: The source is a resource name :)
            let $status := xmldb:copy('%{sourcecol}', '%{destination}', '%{sourceres}')
            return <status>{$status}</status>
        '''

        if self.collection and not source.startswith('/'):
            source = self.collection + '/' + source
        if self.collection and not destination.startswith('/'):
            destination = self.collection + '/' + destination
        try:
            sourcecol, sourceres = source.rsplit('/', 1)
        except ValueError:
            sourcecol = ''
            sourceres = source
        query = self.query(xquery,
                           source      = source,
                           sourcecol   = sourcecol,
                           sourceres   = sourceres,
                           destination = destination)
        query.execute()
        return query

def package_query(xquery, start = 1, limit = None, pretty_xml = False):
    '''
    Package up XQuery in a <query> XML tree

    @type  start: int
    @param start: The offset of the first returned item.
    @type  limit: int or None
    @param limit: The maximum number of results.
    @rtype:  string
    @return: The resulting XML.
    '''

    if limit is None:
        limit = -1

    # Create the XML document.
    from xml.dom.minidom import getDOMImplementation, parseString
    xmlns = 'http://exist.sourceforge.net/NS/exist'
    impl  = getDOMImplementation()
    doc   = impl.createDocument(None, "query", None)
    root  = doc.documentElement
    root.setAttribute('xmlns', xmlns)
    root.setAttribute('max',   str(limit))
    root.setAttribute('start', str(start))

    # Add the XQuery into it.
    elem = doc.createElement('text')
    text = doc.createTextNode(xquery)
    root.appendChild(elem)
    elem.appendChild(text)

    # Set query properties.
    properties = doc.createElement('properties')
    root.appendChild(properties)

    if pretty_xml:
        elem = doc.createElement('property')
        elem.setAttribute('name', 'indent')
        elem.setAttribute('value', 'yes')
        properties.appendChild(elem)

        elem = doc.createElement('property')
        elem.setAttribute('name', 'pretty-print')
        elem.setAttribute('value', 'yes')
        properties.appendChild(elem)

    return root.toxml()
