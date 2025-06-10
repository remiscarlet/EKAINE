#!/usr/bin/env bash
source tools/scripts/generate_models.sh

TMP_DIR=$(mktemp -d)/
SCHEMA_DIR="data/eddn/schemas/"
GEN_DIR_NAME="eddn_models"

copy_schemas $TMP_DIR $SCHEMA_DIR

ORIG=journal-v1.0.json
TMP=journal-v1.0.tmp.json
ORIG_PATH=${TMP_DIR}${ORIG}
TMP_PATH=${TMP_DIR}${TMP}

# Add additional fields to journal-v1.0's Faction object
# Remove disallowed fields from journal-v1.0's Faction object
# Remove disallowed fields from journal-v1.0's Message object
jq '
  .properties.message.properties.Factions.items.properties += {
    "Allegiance": { "type": "string" },
    "FactionState": { "type": "string" },
    "Government": { "type": "string" },
    "Happiness": { "type": "string" },
    "Influence": { "type": "number" },
    "Name": { "type": "string" },
    "ActiveStates": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["State"],
        "properties": { "State": { "type": "string" } }
      }
    },
    "RecoveringStates": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["State"],
        "properties": { "State": { "type": "string" } }
      }
    },
    "PendingStates": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["State"],
        "properties": { "State": { "type": "string" } }
      }
    }
  }
  | .properties.message.properties.Factions.items.properties
    |= del(.HappiestSystem, .HomeSystem, .MyReputation, .SquadronFaction)
  | .properties.message.properties
    |= del(.ActiveFine, .CockpitBreach, .BoostUsed, .FuelLevel, .FuelUsed, .JumpDist,
           .Latitude, .Longitude, .Wanted, .IsNewEntry, .NewTraitsDiscovered, .Traits, .VoucherAmount)
' ${ORIG_PATH} > ${TMP_PATH}

mv ${TMP_PATH} ${ORIG_PATH}
echo $ORIG_PATH

generate_models $TMP_DIR $GEN_DIR_NAME