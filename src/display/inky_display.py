import logging
import threading

from PIL import Image
from inky.auto import auto
from display.abstract_display import AbstractDisplay


logger = logging.getLogger(__name__)

# Inky/impression Firmware + busy-pin wait can stall indefinitely (busy-wait bugs); see pimoroni/inky issues.
DEFAULT_INKY_SHOW_TIMEOUT_S = 180.0

class InkyDisplay(AbstractDisplay):

    """
    Handles the Inky e-paper display.

    This class initializes and manages interactions with the Inky display,
    ensuring proper image rendering and configuration storage.

    The Inky display driver supports auto configuration.
    """
   
    def initialize_display(self):
        
        """
        Initializes the Inky display device.

        Sets the display border and stores the display resolution in the device configuration.

        Raises:
            ValueError: If the resolution cannot be retrieved or stored.
        """
        
        self.inky_display = auto()
        self.inky_display.set_border(self.inky_display.BLACK)

        # store display resolution in device config
        if not self.device_config.get_config("resolution"):
            self.device_config.update_value(
                "resolution",
                [int(self.inky_display.width), int(self.inky_display.height)], 
                write=True)

    @staticmethod
    def _prepare_image_for_inky(image: Image.Image) -> Image.Image:
        """Palettes/alpha can confuse UC8159 path; Pimoroni examples use resized RGB-ish buffers."""
        if image.mode == "RGBA":
            background = Image.new("RGB", image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[3])
            return background
        if image.mode == "P":
            return image.convert("RGB")
        if image.mode not in ("RGB", "L"):
            return image.convert("RGB")
        return image

    def display_image(self, image, image_settings=[]):
        
        """
        Displays the provided image on the Inky display.

        The image has been processed by adjusting orientation and resizing 
        before being sent to the display.

        Args:
            image (PIL.Image): The image to be displayed.
            image_settings (list, optional): Additional settings to modify image rendering.

        Raises:
            ValueError: If no image is provided.
        """

        logger.info("Displaying image to Inky display.")
        if not image:
            raise ValueError(f"No image provided.")

        image = self._prepare_image_for_inky(image)

        inky_saturation = self.device_config.get_config('image_settings').get("inky_saturation", 0.5)
        logger.info(f"Inky Saturation: {inky_saturation}")

        timeout = float(
            self.device_config.get_config("inky_show_timeout_seconds", default=DEFAULT_INKY_SHOW_TIMEOUT_S)
        )
        if timeout <= 0:
            timeout = DEFAULT_INKY_SHOW_TIMEOUT_S

        outcome: list = []

        def _inky_io():
            try:
                try:
                    self.inky_display.set_image(image, saturation=inky_saturation)
                except TypeError:
                    self.inky_display.set_image(image)
                self.inky_display.show()
            except Exception as ex:
                outcome.append(ex)

        worker = threading.Thread(target=_inky_io, name="inky-hw-io", daemon=True)
        worker.start()
        worker.join(timeout=timeout)

        if worker.is_alive():
            logger.error(
                "Inky set_image/show did not finish within %.0fs — busy-wait / SPI stall? "
                "Refresh pipeline wird freigegeben; bitte Hardware prüfen und ggf. inkypi neu starten "
                "(Hintergrund-Thread läuft evtl. noch). Timeout per device.json: inky_show_timeout_seconds.",
                timeout,
            )
            raise TimeoutError(f"Inky hardware update exceeded {timeout:.0f}s")

        if outcome:
            logger.exception("Inky set_image/show failed.")
            raise outcome[0]

        logger.info("Inky hardware update finished (show returned).")