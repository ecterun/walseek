# walseek

Todo: ordered by priority

- Additonal Store information
  - Add store api call to pull data from stores
  - Add store data to final output ( street address, state, zip, etc)

- Throttle online api calls to 5 per second

- Kick off multiple store searches at once (throttle api calls pre-req)
  - pre-req of Throttle online api calls to 5 per second, otherwise we will have failed api calls.

- Add check to make sure seekconfig.py is valid
  - Add api key validation call
  - Validate Store String
  - Validate all required variables exist

- replace jq command line calls with python native lib calls

- cleanup older files older then x days
