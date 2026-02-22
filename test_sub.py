from azure.mgmt.subscription.aio import SubscriptionClient
client = SubscriptionClient(credential=None)
print(hasattr(client, "subscriptions"))
