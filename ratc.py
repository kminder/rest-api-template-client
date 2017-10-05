#!/usr/bin/python

import argparse
import datetime
import getpass
import jinja2, json, jsonpath_rw
import os
import requests
import sys
import yaml

def parseArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument( "-t", "--test", action="store_true", help="test template expansion without submitting request" )
    parser.add_argument( "-e", "--extract", help="extract from body via JSONPath query", metavar="query" )
    parser.add_argument( "-o", "--output", default="shb", help="Output options", metavar="format" )
    parser.add_argument( "context", nargs='*', help="context values and file names" )
    parser.add_argument( "template", nargs=1, help="template file name" )
    args = parser.parse_args()
    return args

def now( format="%Y%m%d%H%M%S" ):
    return datetime.datetime.now().strftime( format )

def user():
    return getpass.getuser()

def createEnvironment():
    environment = jinja2.Environment(
        loader = jinja2.FileSystemLoader( './' ),
        undefined = jinja2.StrictUndefined,
        autoescape=True )
    environment.globals['now'] = now
    environment.globals['user'] = user
    return environment

def loadTemplate( environment, templateFileNames ):
    fileName = templateFileNames[0]
    try:
        template = environment.get_template( fileName )
    except jinja2.exceptions.TemplateSyntaxError as e:
        print "ERROR: Template syntax error: %s at line %d" % (e.message, e.lineno)
        sys.exit( -1 )
    return template

def loadContextFile( context, contextFileName ):
    if not context:
        context = {}
    if contextFileName:
        with open( contextFileName ) as contextFile:
            dict = yaml.load( contextFile )
            context.update( dict )
    return context

def loadContextString( context, contextString ):
    valid = False
    if not context:
        context = {}
    if contextString:
        parts = None
        if "=" in contextString:
            parts = contextString.split( "=" )
        elif ":" in contextString:
            parts = contextString.split( ":" )
        if parts:
            name = parts[0].strip()
            value = ""
            if len( parts ) == 2:
                value = parts[1].strip()
            context[ name ] = value
            valid = True
    if not valid:
        sys.stderr.write( "ERROR: Invalid context string: %s\n" % ( contextString ) )
        sys.exit( -1 )
    return context

def loadContext( contextSources ):
    context = {}
    if contextSources:
        for contextSource in contextSources:
            if os.path.isfile( contextSource ):
                context = loadContextFile( context, contextSource )
            elif "=" in contextSource or ":" in contextSource:
                context = loadContextString( context, contextSource )
            else:
                sys.stderr.write( "ERROR: Invalid context source: %s\n" % ( contextSource ) )
                sys.exit( -1 )
    return context

def renderTemplate( template, context ):
    try:
        return template.render( context )
    except jinja2.exceptions.UndefinedError as e:
        sys.stderr.write( "ERROR: Template value %s\n" % ( e.message ) )
        sys.exit( -1 )

def parseMethodLine( request, line ):
    parts = line.split()
    if not parts or len(parts) == 0:
        print "ERROR: Invalid empty method line"
        sys.exit( -1 )
    if len(parts) == 1:
        print "ERROR: Invalid method line missing address: %s" % ( line )
        sys.exit( -1 )
    request['method'] = parts[0]
    request['url'] = parts[1]
    if len(parts) > 2:
        request['proto'] = parts[2]
    return request

def parseHeaderLine( request, line ):
    parts = line.split(':')
    name = parts[0]
    value = parts[1]
    if not 'headers' in request:
        request['headers'] = {}
    request['headers'][name] = value.strip()
    return request

def parseBodyLine( request, line ):
    if not 'body' in request:
        request['body'] = line
    else:
        body = request['body']
        body += "\n" + line
        request['body'] = body
    return request

def parseRequest( text ):
    request = {}
    lines = text.splitlines()

    state = 'method'
    for line in lines:
        if state == 'body':
            parseBodyLine( request, line )
        else:
            if state == 'method':
                if line.strip() == '':
                    state = 'header'
                else:
                    parseMethodLine( request, line )
                    state = 'header'
            elif state == 'header':
                if line.strip() == '':
                    state = 'body'
                else:
                    parseHeaderLine( request, line )

    return request

def executeRequest( request, context ):
    method = request.get('method')
    if method:
        method = method.uppe()
    proxies = context.get( 'proxies' )
    cookies = context.get( 'cookies' )
    response = None
    try:
        if method == 'GET':
            response = requests.get( url=request['url'], headers=request['headers'], cookies=cookies, proxies=proxies )
        elif method == 'POST':
            response = requests.post( url=request['url'], headers=request['headers'], cookies=cookies, proxies=proxies, data=request['body'] )
        elif method == 'PUT':
            response = requests.put( url=request['url'], headers=request['headers'], cookies=cookies, proxies=proxies, data=request['body'] )
        elif method == 'DELETE':
            response = requests.delete( url=request['url'], headers=request['headers'], cookies=cookies, proxies=proxies )
        else:
            print "ERROR: Invalid method: %s" % (method)
            sys.exit(-1)
    except requests.exceptions.ConnectionError as e:
        print "ERROR: Connection failure: %s" % (e.message)
        sys.exit( -1 )
    except requests.exceptions.RequestException as e:
        print "ERROR: Communication failure: %s" % (e.message)
        sys.exit( -1 )
    return response

def printRequest( request ):
    print "%s %s" % ( request['method'], request['url'] )
    if 'headers' in request:
        for name, value in request['headers'].iteritems():
            print "%s: %s" % ( name, value )
    print
    print "%s" % ( request['body'] )

def isContentTypeResponse( response, contentTypeList, default=False ):
    isContentType = default
    if response.headers and 'Content-Type' in response.headers:
        responseContentType = response.headers['Content-Type'].lower()
        for checkContentType in contentTypeList:
            if checkContentType == responseContentType:
                isContentType = True
                break
    return isContentType

def isJsonResponse( response ):
    return isContentTypeResponse( response, [ "application/json", "text/json" ] )

def printJsonBody( response ):
    j = json.loads( response.text )
    print json.dumps( j, indent=4, sort_keys=True )

def printJsonPathMatches( response, jsonpath ):
    j = json.loads( response.text )
    e = jsonpath_rw.parse( jsonpath )
    f = e.find( j )
    for m in f:
        print m.value

def printResponse( response, args ):
    divide = False
    if not args.extract:
        if "s" in args.output:
            divide = True
            print '%d %s' % ( response.status_code, response.reason )
        if "h" in args.output:
            divide = True
            for name, value in response.headers.iteritems():
                print '%s: %s' % ( name, value )
    if args.extract or "b" in args.output:
        if divide:
            print
        if isJsonResponse( response ):
            if not args.extract:
                printJsonBody( response )
            else:
                printJsonPathMatches( response, args.extract )
        else:
            print response.text

def getExitStatus( response ):
    status = 0
    if response.status_code >= 300:
        status = response.status_code
    return status

def main():
    args = parseArgs();
    templateFileName = args.template
    environment = createEnvironment()
    template = loadTemplate( environment, templateFileName )
    context = loadContext( args.context )
    concrete = renderTemplate( template, context )

    request = parseRequest( concrete )
    if args.test:
        printRequest( request )
        sys.exit( 0 )
    else:
        response = executeRequest( request, context )
        printResponse( response, args )
        sys.exit( getExitStatus( response ) )

if __name__ == "__main__": main()