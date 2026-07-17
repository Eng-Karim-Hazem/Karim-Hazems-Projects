from rpi_ws281x import PixelStrip, Color
import threading
import time

# ==========================================
# Configuration
# ==========================================

LED_COUNT = 16
LED_PIN = 18
LED_FREQ_HZ = 800000
LED_DMA = 10
LED_BRIGHTNESS = 30
LED_INVERT = False
LED_CHANNEL = 0


class LEDController:

    def __init__(self):

        self.strip = PixelStrip(
            LED_COUNT,
            LED_PIN,
            LED_FREQ_HZ,
            LED_DMA,
            LED_INVERT,
            LED_BRIGHTNESS,
            LED_CHANNEL
        )

        self.initialized = False

        self.worker = None

        self.stop = threading.Event()


    # ==========================================

    def initialize(self):

        if self.initialized:
            return

        self.strip.begin()

        self.initialized = True

        self.turn_off()


    # ==========================================

    def turn_off(self):

        self.stop_animation()

        for i in range(LED_COUNT):

            self.strip.setPixelColor(
                i,
                Color(0,0,0)
            )

        self.strip.show()


    # ==========================================

    def set_color(self,r,g,b):

        self.stop_animation()

        for i in range(LED_COUNT):

            self.strip.setPixelColor(
                i,
                Color(r,g,b)
            )

        self.strip.show()


    # ==========================================

    def flash(
        self,
        r,
        g,
        b,
        flashes=2,
        delay=0.18,
        return_ready=False):

        self.stop_animation()

        for _ in range(flashes):

            for i in range(LED_COUNT):
                self.strip.setPixelColor(i, Color(r, g, b))

            self.strip.show()

            time.sleep(delay)

            for i in range(LED_COUNT):
                self.strip.setPixelColor(i, Color(0, 0, 0))

            self.strip.show()

            time.sleep(delay)

        if return_ready:
            self.ready_animation()

    # ==========================================

    def stop_animation(self):

        self.stop.set()

        if self.worker and self.worker.is_alive():

            self.worker.join()

        self.stop.clear()


    # ==========================================

    def start_animation(self,target):

        self.stop_animation()

        self.worker = threading.Thread(

            target=target,

            daemon=True

        )

        self.worker.start()


    # ==========================================

    def ready_animation(self):

        def run():

            shift = 0

            while not self.stop.is_set():

                for i in range(LED_COUNT):

                    t=((i+shift)%LED_COUNT)/(LED_COUNT-1)

                    r=int(120*t)

                    g=int(255*(1-t))

                    b=255

                    self.strip.setPixelColor(
                        i,
                        Color(r,g,b)
                    )

                self.strip.show()

                shift=(shift+1)%LED_COUNT

                time.sleep(0.08)

        self.start_animation(run)


    # ==========================================

    def breathing(self,r,g,b):

        def run():

            while not self.stop.is_set():

                for v in range(31):

                    if self.stop.is_set():

                        return

                    for i in range(LED_COUNT):

                        self.strip.setPixelColor(
                            i,
                            Color(
                                r*v//30,
                                g*v//30,
                                b*v//30
                            )
                        )

                    self.strip.show()

                    time.sleep(0.03)

                for v in range(30,-1,-1):

                    if self.stop.is_set():

                        return

                    for i in range(LED_COUNT):

                        self.strip.setPixelColor(
                            i,
                            Color(
                                r*v//30,
                                g*v//30,
                                b*v//30
                            )
                        )

                    self.strip.show()

                    time.sleep(0.03)

        self.start_animation(run)
    # ==========================================

    def spinner(self,r,g,b,rotations=2,delay=0.05):

        def run():

            total = LED_COUNT * rotations

            for i in range(total):

                if self.stop.is_set():

                    return

                for j in range(LED_COUNT):

                    self.strip.setPixelColor(
                        j,
                        Color(0,0,0)
                    )

                self.strip.setPixelColor(
                    i % LED_COUNT,
                    Color(r,g,b)
                )

                self.strip.show()

                time.sleep(delay)

        self.start_animation(run)


# ===================================================
# Global Controller
# ===================================================

_controller = LEDController()


# ===================================================
# Public Functions
# ===================================================

def initialize():

    _controller.initialize()


def turn_off():

    _controller.turn_off()


def booting():

    _controller.spinner(
        0,
        0,
        255
    )


def ready_scan():

    _controller.ready_animation()


def qr_detected():

    _controller.set_color(
        0,
        0,
        255
    )


def access_granted():

    _controller.flash(
        0,
        255,
        0,
        flashes=2,
        return_ready=True
    )


def access_denied():

    _controller.flash(
        255,
        0,
        0,
        flashes=2,
        return_ready=True
    )


def attendance_active():

    _controller.set_color(
        255,
        220,
        0
    )


def attendance_ended():

    _controller.flash(
        255,
        255,
        255,
        flashes=1,
        return_ready=True
    )


def tamper_alert():

    _controller.flash(
        180,
        0,
        255,
        flashes=4
    )


def heartbeat_lost():

    _controller.flash(
        255,
        0,
        0,
        flashes=6
    )


def offline_cache():

    _controller.breathing(
        255,
        120,
        0
    )


def syncing_cache():

    _controller.spinner(
        0,
        255,
        255
    )