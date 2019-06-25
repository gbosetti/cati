require 'date'

def register(params)

end


def filter(event)
    event.set("timestamp_ms", DateTime.parse(event.get("published")).to_time.to_i)
end