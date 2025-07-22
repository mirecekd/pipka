#!/bin/bash

PROFILE="$1"
SSO_URL="$2"
REGION="$3"
CONFIG_APPEND="$HOME/.aws/config_append"

list_sso_sessions() {
    echo "Existing SSO session profiles:"
    grep -n "\[sso-session" ~/.aws/config | sed 's/\[sso-session //' | sed 's/\]//'
}

if [ $# -ne 3 ]; then
    list_sso_sessions
    echo "Usage: $0 PROFILE SSO_URL REGION"
    exit 1
fi

if grep -q "\[sso-session $PROFILE\]" ~/.aws/config; then
    echo "SSO session profile '$PROFILE' already configured."
    list_sso_sessions
    exit 1
fi


output() {
    echo "$1"
    echo "$1" >> "$CONFIG_APPEND"
}

> "$CONFIG_APPEND"

# Přidání [sso-session] sekce
output "[sso-session $PROFILE]"
output "sso_start_url = $SSO_URL"
output "sso_region = $REGION"
output "sso_registration_scopes = sso:account:access"
output ""

if [ -s "$HOME/.aws/config" ]; then
    {
        echo
        echo 
        cat "$CONFIG_APPEND"
    } >> "$HOME/.aws/config"
else
    cat "$CONFIG_APPEND" > "$HOME/.aws/config"
fi

[ -f "$CONFIG_APPEND" ] && rm "$CONFIG_APPEND"

aws sso login --use-device-code --sso-session "$PROFILE"

sleep 5 # wtf?

TOKEN=$(grep -l $SSO_URL ~/.aws/sso/cache/*.json | xargs cat | jq -r '.accessToken')

if [ -z "$TOKEN" ]; then
    echo "Nepodařilo se získat access token."
    exit 1
fi

ACCOUNTS=$(aws sso list-accounts --region "$REGION" --access-token "$TOKEN" --output json)

echo "$ACCOUNTS" | jq -r '.accountList[] | @base64' | while read account; do
    _jq() {
        echo ${account} | base64 --decode | jq -r ${1}
    }

    ACCOUNT_ID=$(_jq '.accountId')
    ACCOUNT_NAME=$(echo $(_jq '.accountName') | sed 's/[^a-zA-Z0-9]/-/g')    

    ROLES=$(aws sso list-account-roles --account-id "$ACCOUNT_ID" --access-token "$TOKEN" --region "$REGION" --output json)

    echo "$ROLES" | jq -r '.roleList[] | @base64' | while read role; do
        _jq_role() {
            echo ${role} | base64 --decode | jq -r ${1}
        }

        ROLE_NAME=$(_jq_role '.roleName')

        output "[profile $PROFILE-${ACCOUNT_NAME}-${ROLE_NAME}]"
        output "sso_session = $PROFILE"
        output "output = json"
        output "sso_role_name = $ROLE_NAME"
        output "region = $REGION"
        output "sso_account_id = $ACCOUNT_ID"
        output ""
    done
done

# Přidání obsahu config_append do config
if [ -s "$HOME/.aws/config" ]; then
    {
        echo
        echo 
        cat "$CONFIG_APPEND"
    } >> "$HOME/.aws/config"
else
    cat "$CONFIG_APPEND" > "$HOME/.aws/config"
fi
