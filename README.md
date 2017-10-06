# REST API Template Client

A simple command line tool to invoke REST APIs.
A template is used to define the static content of the request.
Template variables are populated from extenal context.

## Quick Start

```bash
> ratc.py context.yaml template.rat
``` 

Templates use the Jinja2 template syntax and are in general formatted similar to a HTTP request as shown below.

```
POST http://{{{api_host}}:80/{{api-path}}
Content-Type: application/json

{
    "{{api_key}}": "{{api_value}}"
}
```

Context values for template expansion can be provided via one or more files in YAML format.

```yaml
api_host: example-host
api_path: example-path/
api_key: example-key
api_value: example-value
```

The resulting request would be as follows.

```jinja2
POST http://example-host:80/example-path/
Content-Type: application/json

{
    "example-key": "example-value"
}
```

Context values can be overriden on the command line.

```bash
> ratc.py context.yaml api_host=different-host template.rat
```

Multiple context files and values can be povided.

```bash
> ratc.py context.yaml more-context.yaml api_host=different-host api_value=different-value template.rat
```  

## Usage

```bash
usage: ratc.py [-h] [-t] [-e query] [-o format]
               [context [context ...]] template

positional arguments:
  context               context values and file names
  template              template file name

optional arguments:
  -h, --help            show this help message and exit
  -t, --test            test template expansion without submitting request
  -e query, --extract query
                        extract from body via JSONPath query
  -o format, --output format
                        Output options
```
## Functions

There are built in functions that can be used in templates.

- now() - Retuns the current date/time in YYYYMMddhhmmss format.
- user() - Retuns the name of the currrent user.  

## Proxies
Proxies can be configured in one of two ways.
1. Environment variables HTTP_PROXY and HTTP_PROXY.
```bash
export HTTP_PROXY=http://<your_proxy_host>:<your_proxy_port
export HTTPS_PROXY=http://<your_proxy_host>:<your_proxy_port
```
2. Special context values.
```yaml
proxies:
  http: http://<your_proxy_host>:80
  https: http://<your_proxy_host>:80
```
These would typically be used in conjunction with other context information.
```bash
> ratc.py context.yaml proxies.yaml template.rat
```

## Cookies
Cookies can be provided using special context values.
```yaml
cookies:
  cookie_name_one: cookie_value_one
  cookie_name_two: cookie_value_two
```
These would typically be used in conjunction with other context information.
```bash
> ratc.py context.yaml cookies.yaml template.rat
```

## Extacting response values
Information can be extracted from JSON responses using JSONPath syntax.
```bash
> ratc.py -e <jsonpath expression> template.rat
```

## Formatting output
The information output can be controlled by the -o parameter.
The value of this parameter can be any combination of the following:
- s - Display the status code and text.
- h - Display the response headers.
- b - Display the response body.

Note: If an extaction query is used then the output will be forced to -o b.

