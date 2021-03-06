from __future__ import print_function

import datetime
import os

try:
    import astral
    HAVE_ASTRAL = True
except ImportError:
    HAVE_ASTRAL = False


class Module(object):
    def __init__(self, boot):
        self._boot = boot
        self._ready = False

        print("Sunrise at {}. Sunset at {}".format(self._parse_time("sunrise"),self._parse_time("sunset")))

        # Initialize schedule.
        if os.environ.get('SCHEDULE_MONTHLY', '0') == '1':
            # Month-dependent schedule.
            month = datetime.date.today().month

            schedule_start = self._parse_time(os.environ.get('SCHEDULE_MONTH{}_START'.format(month), '08:00'))
            schedule_end = self._parse_time(os.environ.get('SCHEDULE_MONTH{}_END'.format(month), '18:00'))
            schedule_t_off = self._parse_duration(os.environ.get('SCHEDULE_MONTH{}_T_OFF'.format(month), '35'))
            schedule_t_on = self._parse_duration(os.environ.get('SCHEDULE_MONTH{}_T_ON'.format(month), '15'))
        else:
            # Static schedule.
            schedule_start = self._parse_time(os.environ.get('SCHEDULE_START', '08:00'))
            schedule_end = self._parse_time(os.environ.get('SCHEDULE_END', '18:00'))
            schedule_t_off = self._parse_duration(os.environ.get('SCHEDULE_T_OFF', '35'))  # Time in minutes.
            schedule_t_on = self._parse_duration(os.environ.get('SCHEDULE_T_ON', '15'))  # Time in minutes.

        if not schedule_start or not schedule_end or schedule_t_off is None or schedule_t_on is None:
            print("WARNING: Ignoring malformed schedule specification, using safe values.")
            schedule_start = self._parse_time('00:01')
            schedule_end = self._parse_time('23:59')
            schedule_t_off = self._parse_duration('59')  # Time in minutes.
            schedule_t_on = self._parse_duration('1')  # Time in minutes.

        self._started = datetime.datetime.now()
        self._schedule_start = schedule_start
        self._schedule_end = schedule_end
        self._on_duration = schedule_t_on
        self._off_duration = schedule_t_off
        self._ready = True

    def _parse_time(self, time):
        """Parse time string (HH:MM)."""
        if HAVE_ASTRAL:
            try:
                location = astral.Location((
                    'Unknown',
                    'Unknown',
                    float(os.environ['LATITUDE']),
                    float(os.environ['LONGITUDE']),
                    'UTC',
                    0
                ))

                if time == 'sunrise':
                    return location.sunrise().time()
                elif time == 'sunset':
                    return location.sunset().time()
            except (KeyError, ValueError):
                pass

        try:
            hour, minute = time.split(':')
            return datetime.time(hour=int(hour), minute=int(minute), second=0)
        except (ValueError, IndexError):
            return None

    def _parse_duration(self, duration):
        """Parse duration string (in minutes)."""
        try:
            return datetime.timedelta(minutes=int(duration))
        except ValueError:
            return None

    def process(self, modules):
        """Check if we need to shutdown."""
        if not self._ready:
            return

        # Check if we have been online too long and shutdown.
        if (datetime.datetime.now() - self._started) >= self._on_duration:
            print("Have been online for too long, need to shutdown.")
            self._boot.shutdown = True

    def shutdown(self, modules):
        """Compute next alarm before shutdown."""
        if not self._ready:
            return

        # Check voltage to configure boot interval
        voltage = self._boot.sensor_mcp.get_voltage()

        if not voltage > os.environ.get('POWER_THRESHOLD_HALF', '0'):
            # Lower voltage then half threshold, doubling the sleep length
            self._off_duration = self._off_duration * 2
            print("Low voltage warning, doubling sleep duration")
        elif not voltage > os.environ.get('POWER_THRESHOLD_QUART', '0'):
            # Less voltage then quarter threshold, quadrupling the sleep length
            self._off_duration = self._off_duration * 4
            print("Low voltage warning, quadrupling sleep duration")
        else:
            # Sufficient power, continue as planned
            pass

        current_time = self._boot.rtc.current_time
        wakeup_time = None
        if self._schedule_end >= self._schedule_start and current_time.time() > self._schedule_start and current_time.time() < self._schedule_end:
            wakeup_time = (current_time + self._off_duration).time()
        elif self._schedule_end < self._schedule_start and ((current_time.time() < self._schedule_start and current_time.time() < self._schedule_end) or (current_time.time() >= self._schedule_start and current_time.time() >= self._schedule_end)):
            wakeup_time = (current_time + self._off_duration).time()
        else:
            wakeup_time = self._schedule_start

        print("Scheduling next wakeup at {}.".format(wakeup_time.isoformat()))
        self._boot.rtc.alarm1_time = wakeup_time
