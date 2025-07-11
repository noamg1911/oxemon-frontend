# `oxemon` Frontend

This is the frontend side of the glorious oxemon.<br>
It is an easy-to-operate framework for defining and viewing metrics of data generated using `oxemon agent`.

## TL;DR

### Prerequisites

- `docker` and `docker-compose`
- Some tool to run `Makefile`s (only relevant for Windows)
- You need to have `python3` installed

### 0. Initial Setup

⚠️ This needs to be done only once (re-run when updating to newer versions of `oxemon-frontend`).

1. Clone this repo (`oxemon-frontend`) and `cd` into it.
1. In this folder, run
```bash
make build
```

### 1. Configuration

⚠️ This needs to be done everytime you add `emit` calls in your code (which changes the dictionary) or when you want to update your metrics configurations.

1. Get the path to your `oxemon_dictionary.json` file (**auto-generated** by the oxemon agent).
2. Write a [metrics configuration](#metrics-configuration) for your project.
3. From this folder, run
```bash
make config dictionary=<path/to/oxemon_dictionary.json> metrics=<path/to/metrics.yaml> output=<output/folder>
```

### 2. Start

⚠️ This starts/stops the servers, and they should be restarted whenever the configuration is changed.

To start/stop the servers, simply run
```bash
make start CONFIG_FOLDER=<path/to/oxemon/configuration/folder>
make stop
```

_Do you want to support cool reinitialization without taking down the servers? You're more than welcome to iplement this feature and open a Pull Request._

### 3. Look at the Dashboards

Go to http://localhost:3000/dashboards and view your dashboards!

## Metrics Configuration

To see your metrics with `oxemon`, you need to define what metrics on which events you want to see.<br>
This is done through a configuration file (a.k.a `metrics.yaml`).

We'll explain its structure using the [example file](example/metrics.yaml).

### Events
Each top-level key defines an event to listen to. An event, as defined by `oxemon` is a combination of `module_id` and an `event_id`. Basically, the first means "where the event came from" and the second means "what event happened". See `oxemon agent` for more information on what they mean, how they differ and why they exist.

In our example we monitor 2 events, called `example_counter` and `example_state`.
These names are up to the user, and are shown in the name of the metric in the dashboard.

All module ids and event ids that are available in your code are shown in the auto-generated `oxemon_dictionary.json`, and you are expected to use it as help when building your configuration file.

**Tip!** In `oxemon_dictionary.json` there is a list called `expected_couplings` which includes combinations of known `module_id`s and `event_id`s that are found in your code (for example, hard-coded usages). They dramatically simplify the act of finding what possible events you can look at.

> Note that you do not need (and shouldn't!) touch the `oxemon_dictionary.json` file. It is auto generated and for you to **use**.

### Event Configuration

Each event in the configuration file has 4 required fields:

- `type`: Type of the event (explained [below](#event-types-and-supported-metrics)).
- `module_id`: The module name correlating to the wanted event.
- `event_id`: The event name correlating to the wanted event.
- `operations`: This is a list of metrics to show for that event, and its options are dependant on the type of the event. [See below](#event-types-and-supported-metrics) for more information.

### Event Types and Supported Metrics

`oxemon` currently supports 2 kinds of information monitoring: counters and enumerations.

#### Counters
These are numeric (unsigned) values, which are come to monitor sizes and amounts.

Their `type` in the configuration is **`counter`**.

Common usages include:
- How many bytes were received?
- How much time does some repeating action take?

The **supported metrics** for a counter are:
- `sum`: Shows the overall sum of the received events from when they started to arrive.
- `rolling_average`: A time-based rolling average of the values emitted in this event.

#### Enumerations
These are numeric (unsigned) values, which are used to monitor states and values.

Their `type` in the configuration is **`enum`**.

Common usages include:
- Current state in a state machine.
- Information about having (or not having) configured information.
- Notifying that something was loaded/deleted.

## System Details

Want to understand how this system works and how it is built? Maybe you want to add your own feature and you need some more information, or maybe you are just curios. Either way, you arrived at the correct place.

### Architecture

#### Frontend

The frontend of `oxemon` (this repo) is deployed as a docker-based solution, including 3 components: 
- `grafana`: The actual dashboards and frontend
- `prometheus`: Acts as the middle-man data-pipe. It injects infomation into `grafana` from received events.
- `oxemon_adapter`: This is a custom (Python based) docker which gets information emitted by the `oxemon` agent (the project) and adapts it to prometheus events.

All components are configured by us to automatically connect smoothly with each other.
Just as examples, this includes:
- Configuring prometheus as a "data source" for grafana.
- Automatic creation of grafana dashboards, with names matching the emitted events.

#### Agent

The agent is built as a library designed to be integrated directly inside a project's code, and it emits events out of the project (through a user-defined data-tunnel) to be collected by the adapter.

It comes with a utility script to scrape all usages of `oxemon`, and create a conversion dictionary which is later used in the adapter to identify and translate messages.

### Information Emitted

TODO: Maybe add the exact ICD used.

#### Hashing and Translation
To lessen data transfer, and to avoid unnessesary strings in your binary, `oxemon` hashes all strings (module ids, event ids, etc.) and uses only numbers.<br>
This means that the resulting code will now have the strings in it, and that these numbers will be sent instead.

Using the dictionary generated by the agent, the adapter later transltes these numbers back to their original meaning, and the user can seamlessly only use the names and strings of everything.

The conversion file, which is generated by `oxemon`'s agent, used by the adapter when receiving events, and used by the user for building the metric configuration file is known as *`oxemon_dictionary.json`*.

## Future Features

- [frontend] Add "min interval" to generated configurations so that the updates are continuous instead of once every 15 seconds.
- [frontend] Change dashboard creation script so that the yaml defines the dashboards (as top-level keys in the yaml) instead of auto-grouping using module ids.
- [frontend] Refactor: Don't re-generate a new grafana api key every time. Use a mount to give it an existing one.
- [frontend + agent] Support (out of the box) oxemon emit over serial (not just udp) - in both agent and adapter.
- [frontend] Support configuring where we see logs (not always there…)
- [frontend] Support log filtering
- [frontend + agent] Support different levels of events during compilation (shutting off some of the events), making it possible to create different "visibility levels" of the project.

