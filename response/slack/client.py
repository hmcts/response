import logging
import time

import slack_sdk
import os
from slugify import slugify

logger = logging.getLogger(__name__)


class SlackError(Exception):
    def __init__(self, message, slack_error=None):
        self.message = message
        self.slack_error = slack_error


class SlackClient(object):
    def __init__(
        self,
        api_token,
        max_retry_attempts=10,
        retry_base_backoff_seconds=0.2,
        retryable_errors=None,
    ):
        self.api_token = api_token
        self.client = slack_sdk.WebClient(os.environ["SLACK_TOKEN"], timeout=30)
        self.max_retry_attempts = max_retry_attempts
        self.retry_base_backoff_seconds = retry_base_backoff_seconds
        self.retryable_errors = retryable_errors or ["ratelimited"]

    def users_list(self):
        logger.info("Listing Slack users")
        return self.client.users_list(self)

    def get_paginated_users(self, limit=0, cursor=None):
        response = self.client.users_list(limit=limit, cursor=cursor)
        return response

    def get_user_id(self, name):
        logger.info(f"Getting user ID for {name}")
        response = self.users_list()
        for user in response["members"]:
            if user["name"] == name:
                return user["id"]
        raise SlackError(f"User '{name}' not found")

    def get_channel_name(self, id_):
        try:
            response = self.client.conversations_info(channel=id_)
            return response["channel"]["name"]
        except SlackError as e:
            if e.slack_error == "channel_not_found":
                return None
            raise

    def get_channel_id(self, name, auto_unarchive=False):
        logger.info(f"Getting channel ID for {name}")
        next_cursor = None

        while next_cursor != "":
            response = self.client.conversations_list(                
                exclude_archived=not auto_unarchive,
                exclude_members=True,
                limit=800,
                cursor=next_cursor,
            )

            # see if there's a next_cursor
            try:
                next_cursor = response["response_metadata"]["next_cursor"]
                logger.info(f"get_channel_id - next_cursor == [{next_cursor}]")
            except LookupError:
                logger.error(
                    "get_channel_id - I guess checking next_cursor in response object didn't work."
                )

            for channel in response["channels"]:
                if channel["name"] == name:
                    if channel["is_archived"] and auto_unarchive:
                        self.unarchive_channel(channel["id"])
                    return channel["id"]

        raise SlackError(f"Channel '{name}' not found")

    def get_usergroup_id(self, group_handle):
        response = self.client.usergroups_list()
        if not response.get("ok", False):
            raise SlackError(
                f"Failed to get usergroup with group handle {group_handle} : {response['error']}"
            )
        for group in response["usergroups"]:
            if group["handle"] == group_handle:
                return group["id"]
        return None

    def get_usergroup_users(self, group_id):
        response = self.client.usergroups_list(include_users=True)

        if not response.get("ok", False):
            raise SlackError(
                f"Failed to get users from usergroup with id {group_id} : {response['error']}"
            )
        for group in response["usergroups"]:
            if group["id"] == group_id:
                return group["users"]
        return None

    def create_channel(self, name):
        response = self.client.conversations_create(name=name)
        try:
            return response["channel"]["id"]
        except KeyError:
            raise SlackError(
                "Got unexpected response from Slack API for conversations.create - couldn't find channel.id key"
            )

    def get_or_create_channel(self, channel_name, auto_unarchive=False):
        try:
            return self.create_channel(channel_name)
        except SlackError as e:
            if e.slack_error != "name_taken":
                # some other error, let's propagate it upwards
                raise

            return self.get_channel_id(channel_name, auto_unarchive)

    def set_channel_topic(self, channel_id, channel_topic):
        return self.client.conversations_setTopic(channel=channel_id, topic=channel_topic)

    def unarchive_channel(self, channel_id):
        response = self.client.conversations_unarchive(channel=channel_id)
        if not response.get("ok", False):
            raise SlackError(f"Couldn't unarchive channel {channel_id}")

    def send_message(self, channel_id, text, attachments=None, thread_ts=None):
        return self.client.chat_postMessage(
            channel=channel_id,
            text=text,
            attachments=attachments,
            thread_ts=thread_ts,
        )

    def send_ephemeral_message(self, channel_id, user_id, text, attachments=None):
        return self.client.chat_postEphemeral(
            channel=channel_id,
            text=text,
            user=user_id,
            attachments=attachments,
        )

    def send_or_update_message_block(self, channel_id, blocks, fallback_text, ts=None):
        if not ts:
            return self.client.chat_postMessage(
                text=fallback_text, channel=channel_id, ts=ts, blocks=blocks
            )
        else:
            return self.client.chat_update(
                text=fallback_text, channel=channel_id, ts=ts, blocks=blocks
        )

    def add_reaction(self, reaction, channel_id, thread_ts):
        try:
            return self.client.reactions_add(
                name=reaction, channel=channel_id, timestamp=thread_ts
            )
        except SlackError as e:
            if e.slack_error != "already_reacted":
                raise

    def remove_reaction(self, reaction, channel_id, thread_ts):
        try:
            return self.client.reactions_remove(
                name=reaction,
                channel=channel_id,
                timestamp=thread_ts,
            )
        except SlackError as e:
            if e.slack_error != "no_reaction":
                raise

    def get_slack_token_owner(self):
        """
        return the id of the user associated with the current slack token
        """
        try:
            return self.client.auth_test()["user_id"]
        except KeyError:
            raise SlackError(
                "Got unexpected response from Slack API for auth.test - couldn't find user_id key"
            )

    def invite_user_to_channel(self, user_id, channel_id):
        return self.client.conversations_invite(channel=channel_id, users=user_id)

    def join_channel(self, channel_id):
        return self.client.conversations_join(channel=channel_id)

    def leave_channel(self, channel_id):
        return self.client.conversations_leave(channel=channel_id)

    def get_user_profile(self, user_id):
        if not user_id:
            return None

        response = self.client.users_info(user=user_id)

        return {
            "id": user_id,
            "name": response["user"]["name"],
            "fullname": response["user"]["profile"]["real_name"],
            "email": response["user"]["profile"].get("email", None),
            "deleted": response["user"]["deleted"],
        }

    def get_user_profile_by_email(self, email):
        if not email:
            return None

        response = self.client.users_lookupByEmail(email=email)

        return {
            "id": response["user"]["id"],
            "name": response["user"]["name"],
            "fullname": response["user"]["profile"]["real_name"],
            "email": email,
            "deleted": response["user"]["deleted"],
        }

    def rename_channel(self, channel_id, new_name):
        prefix = ""
        if not (new_name.startswith("inc-") or new_name.startswith("#inc-")):
            prefix = "inc-"

        new_name = slugify(f"{prefix}{new_name}", max_length=80)
        
        return self.client.conversations_rename(channel=channel_id, name=new_name)

    def dialog_open(self, dialog, trigger_id):
        return self.client.dialog_open(trigger_id=trigger_id, dialog=dialog)
