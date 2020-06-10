# hivequeue
A txjsonrpcqueue inspired async python client library for the HIVE JSON-RPC API.

This python library is based on the txjsonrpcqueue library. While txjsonrpcqueue wasn't completely STEEM specific, its primary target platform was STEEM. As you might know, STEEM has been severely compromized by a decentralization attack. As a developer I don't want to support this compromizes blockchain, and keeping txjsonrpcqueue would mean I will do just that. I'm starting hivequeue from scratch with the explicit goal of creating an asynchonous python library for HIVE that doesn't support STEEM. I'm adding an extra clause to the copyright notice of this new library stating that hivequeue may not legally be forked to code that supports either the STEEM or TRX blockchain. 

## TODO

* Test rate limit implementation with sufficient code coverage.
* Write aiohttp based JSON-RPC client with one per API node instance per queue and per API node config.
* Add configs for *Blurt* as well. 
* Create a *txjsonrpcqueue* inspired hysteresis API queue.
* Create a design for best fit-in for block streaming in life mode.
* Add 6.5 day and 7,0 day fixed-delay streaming support.
* Add dead-stream support with date range.
* Add helpers for async mappings to client side hive keychain operations.
* Add signing code *for custom_json operations only*. Hivequeue is not meant as a library for bots. It's meant as a library for DApps and chain monitoring apps!

 
