#!/usr/bin/env python
#


# DeltaTime
#
class DeltaTime():
    # __init__
    #
    def __init__(self, date, now):
        now = now.replace(tzinfo=None)
        delta = now - date.replace(tzinfo=None)

        sec_p_hr = 60 * 60
        self.__hours = delta.seconds / sec_p_hr
        dhs = self.__hours * sec_p_hr
        remaining_seconds = delta.seconds - dhs

        self.__minutes = (delta.seconds - dhs) / 60
        dhm = self.__minutes * 60
        self.__seconds = remaining_seconds - dhm

        if delta.days < 1:
            self.__days = 0
        else:
            self.__days = delta.days

        return

    @property
    def days(self):
        return self.__days

    @property
    def hours(self):
        return self.__hours

    @property
    def minutes(self):
        return self.__minutes

    @property
    def seconds(self):
        return self.__seconds

# vi:set ts=4 sw=4 expandtab:
