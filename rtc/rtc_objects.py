
class RtcStream(object):

    def __init__(self, name, rtc_url):
        self.name = name
        self.rtc_url = rtc_url

    def __eq__(self, other):
        if not isinstance(other, RtcStream):
            return False
        return ((self.name == other.name) and (self.rtc_url == other.rtc_url))

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return "RtcStream('%s', '%s')" % (self.name, self.rtc_url)

    def __hash__(self):
        return hash((self.name, self.rtc_url))


class RtcWorkspace(object):

    def __init__(self, name, rtc_url):
        self.name = name
        self.rtc_url = rtc_url


class RtcComponent(object):

    def __init__(self, name, stream, baseline, rtc_url):
        self.name = name
        self.stream = stream
        self.baseline = baseline
        self.rtc_url = rtc_url
