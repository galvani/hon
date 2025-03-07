import ssl
import socket
import asyncio
import logging
from pathlib import Path
import shutil
import certifi
from typing import Optional

try:
    from homeassistant.core import HomeAssistant as HA
except ImportError:
    print("Home Assistant not found. Running standalone.")
    HA = None

_LOGGER = logging.getLogger(__name__)

def get_ssl_certificate(hostname: str = "account2.hon-smarthome.com", port: int = 443, output_file: str = "hon-smarthome.crt") -> None:
    """
    Retrieve an SSL certificate from a given hostname and save it in PEM format.

    Args:
        hostname (str): The hostname from which to retrieve the certificate.
        port (int): The port to use for the connection.
        output_file (str): The file path to save the certificate.
    """
    # Create an unverified SSL context (bypasses certificate verification).
    context = ssl._create_unverified_context()

    # Connect to the server and wrap the socket with the unverified context.
    with socket.create_connection((hostname, port)) as sock:
        with context.wrap_socket(sock, server_hostname=hostname) as ssock:
            # Retrieve the certificate in binary (DER) form.
            der_cert: Optional[bytes] = ssock.getpeercert(binary_form=True)
            if der_cert is None:
                raise ValueError("Failed to retrieve certificate")
            # Convert it to PEM format.
            pem_cert = ssl.DER_cert_to_PEM_cert(der_cert)

    # Write the PEM-formatted certificate to a file.
    with open(output_file, "w") as cert_file:
        cert_file.write(pem_cert)

    print(f"Certificate saved to {output_file}")

async def update_ca_certificates(hass: Optional[HA]) -> bool:
    """
    Update the CA certificates in the Certifi bundle by appending a custom certificate.

    If the custom certificate file (RapidSSL_TLS_RSA_CA_G1.crt) is missing,
    it falls back to retrieving it using `get_ssl_certificate`.
    """
    # Determine paths for the Certifi bundle and its backup.
    certifi_bundle_path = Path(certifi.where())
    _LOGGER.debug(f"Certifi CA bundle path: {certifi_bundle_path}")
    certifi_backup_path = certifi_bundle_path.with_suffix(certifi_bundle_path.suffix + ".bak")

    # Determine the location of the custom certificate file.
    rapidssl_ca_path = Path(__file__).with_name("RapidSSL_TLS_RSA_CA_G1.crt")
    cert_name = rapidssl_ca_path.stem.replace("_", " ")

    # Backup Certifi bundle.
    # Create a backup of the current Certifi bundle.
    await hass.async_add_executor_job(shutil.copyfile, certifi_bundle_path, certifi_backup_path)

    # If the custom certificate file is missing, fall back to retrieving it.
    if not rapidssl_ca_path.exists():
        _LOGGER.warning(
            "RapidSSL CA certificate not found. Falling back to retrieving certificate using get_ssl_certificate."
        )
        # Call get_ssl_certificate in the executor; note that we pass the path as a string.
        await hass.async_add_executor_job(
            get_ssl_certificate,
            "account2.hon-smarthome.com",
            443,
            str(rapidssl_ca_path)
        )

    # Read the contents of the Certifi bundle and the custom certificate.
    cacerts, rapidssl_ca = await asyncio.gather(
        *(hass.async_add_executor_job(path.read_text) for path in (certifi_bundle_path, rapidssl_ca_path))
    )

    # If the custom certificate is not already in the bundle, append it.
    if rapidssl_ca not in cacerts:
        cacerts += f"\n# Haier hOn: {cert_name}\n"
        cacerts += rapidssl_ca
        await hass.async_add_executor_job(certifi_bundle_path.write_text, cacerts)
        _LOGGER.error(
            f"{cert_name} -> loaded into Certifi CA bundle. Restart Home Assistant to apply changes."
        )
        return True

    return False

if __name__ == "__main__":
    get_ssl_certificate()