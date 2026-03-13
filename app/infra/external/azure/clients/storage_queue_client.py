from azure.core.credentials import TokenCredential
from azure.storage.queue import BinaryBase64DecodePolicy, BinaryBase64EncodePolicy
from azure.storage.queue.aio import QueueClient


class AzureStorageQueueClient:
    """
    Azure Storage Queue Client Factory.
    Centralizes QueueClient creation logic.
    """

    def get_queue_client(
        self, account_name: str, queue_name: str, credential: TokenCredential
    ) -> QueueClient:
        queue_url = f"https://{account_name}.queue.core.windows.net"
        return QueueClient(
            account_url=queue_url,
            queue_name=queue_name,
            credential=credential,
            message_encode_policy=BinaryBase64EncodePolicy(),
            message_decode_policy=BinaryBase64DecodePolicy(),
        )
