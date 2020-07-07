# BLURT per-API-node config files.

## NOTE: JSON data structure hasn't fully solidified yet.

If you are reading this and happen to be the maintainer of one of the nodes listed, 
or of a node not listed, pull requests for the config file for clients of your API-node
are welcome. Or even better, take the config file for your node and put it in its own 
github repo and create an issue for a sumbodule link from this repo.


A config file looks like this. 
```json
[{
    "host": "rpc.blurt.world",
    "protocol": "https",
    "enabled": true,
    "rate_limit" : {
        "simulate": true,  
        "smoothen": true,
        "window": 60,
        "limit": 600
    },
    "batch": {
        "enabled": true,
        "max_batch": 20
    },
    "api": {
        "chain": "BLURT",
        "version": "0.23.0",
        "apikey": {
            "enabled": false
        }
    }
}]
```

Or possibly like:

```json
[{
    "host": "demo.blurt.timelord.ninja",
    "protocol": "https",
    "enabled": false,
    "port": 6443,
    "rate_limit" : {
        "simulate": false,
        "smoothen": true
    },
    "batch": {
        "enabled": true,
        "max_batch": 1
    },
    "api": {
        "chain": "BLURT",
        "version": "0.23.0",
        "apikey": {
            "enabled": true,
            "optional": true,
            "mode": "query_field",
            "acquire": "hq_api_challenge",
            "batch": {
                "enabled": true,
                "max_batch": 50
            }
        },
        "sub_api": {
          "include": ["condenser"]
        }
    }
},{
    "host": "demo.blurt.timelord.ninja",
    "protocol": "http",
    "enabled": false,
    "port": 6080,
    "rate_limit" : {
        "simulate": false,
        "smoothen": true
    },
    "api": {
        "chain": "BLURT",
        "version": "0.23.0",
        "apikey": {
            "enabled": true,
            "optional": false,
            "mode": "query_field",
            "acquire": "hq_api_challenge",
            "batch": {
                "enabled": true,
                "max_batch": 50
            }
        },
        "sub_api": {
          "include": ["condenser"]
        }
    }

}]
```

# host
The dns name of a full-API host

# protocol
The protocol this config object applies to. Currently **http** or **https**, in the future web sockets may get supported also.

# enabled
Boolean indicating the config and the API node have been tested and both are ready for production use.

# port

Optional TCP port number. By default 443 (https) or 80 (http) is used.

# rate limit

## smoothen
Try to produce request less bursty by spreading request over the available quota for the current time window.

## simulate
Host doesn't implement **draft-polli-ratelimit-headers-00**, simulate rate limit with below params.

## window
The amount of seconds per rate limiting window. Only used when *simulate* is **true**.

## limit
The amount of HTTP requests per time window. Only used when *simulate* is **true**.

# batch

## enabled
Use JSON-RPC batching request. Otherwise a single JSON-RPC request without square brackets is used as request.

## max\_batch
Maximum amount of JSON-RPC requests per JSON-RPC batch.

# api

## chain
The name of the blockchain ("BLURT")

## version
The version string for the currently supported version of the API

## apikey

### enabled
Flag indicating if the node supports a premium QOS mode using an API key.

### optional
Flag indicating if the premium QOS mode is optional.

### mode
This field indicates how the API-key is to be communicated. Modes currently defined are:

* query\_field
* request\_header

### acquire
Defines the way in what the user is supposed to acquire the API-key. Values currently defined are:

* static  : Static API-Node admin supplied API-key
* hq\_api\_challenge : Two step acquisition using signing of a server side chalange. 

### batch
A batch section here overrules the global batch section for API-key using JSON-RPC queries.

## sub\_api

### include
API node only supports given list of sub-APIs

### exclude
API node supports all sub APIs except for the ones specified as list here.
