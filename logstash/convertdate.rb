require 'date'

def register(params)
    @date_field = params["date_field"]
    @date_format = params["date_format"]
end


def filter(event)
    #event.set("timestamp_ms", DateTime.parse(event.get("published")).to_time.to_i)
    #event.set("timestamp_ms", DateTime.parse(event.get("published")).strftime('%Q'))
    #timestamp = DateTime.parse(event.get("published")).to_time
    timestamp = DateTime.strptime(event.get(@date_field), @date_format).strftime('%Q')
    event.set("timestamp_ms", timestamp )
    return [event]
end