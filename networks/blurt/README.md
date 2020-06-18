# BLURT per-API-node config files.

If you are reading this and happen to be the maintainer of one of the nodes listed, or of a node not listed,
pull requests for the config file for clinets of your API node are welcome. Or even better, take the config 
file for your node and put it in its own github repo and create an issue for a sumbodule link from this repo.

A config file looks like this.
```json
{
    "host": "api.blurt.io",
    "enabled": true,
    "ssl": true,
    "rate_limit" : {
        "simulate": true,
        "smoothen": true,
        "window": 60,
        "limit": 600
    },
    "batch": {
        "enabled": true,
        "max_batch": 20
    }
}
```

## host
The dns name of a full-API host

## enabled
Boolean indicating the config and the API node have been tested and both are ready for production use.

## ssl
Boolean indicating https (true) or http (false)

## rate limit

### smoothen
Try to produce request less bursty by spreading request over the available quota for the current time window.

### simulate
Host doesn't implement **draft-polli-ratelimit-headers-00**, simulate rate limit with below params.

### window
The amount of seconds per rate limiting window.

### limit
The amount of HTTP requests per time window.

## batch

### enabled
Use JSON-RPC batching request.

### max\_batch
Maximum amount of JSON-RPC requests per JSON-RPC batch.
