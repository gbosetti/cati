require 'time'

def register(params)
    @date_field = params["date_field"]
    @date_format = params["date_format"]
end


def filter(event)

    event_date = event.get(@date_field)

    begin
        timestamp = Time.parse(event_date).to_time.to_i.to_s
        event.set("timestamp_ms", timestamp )

    rescue Exception => ex
      event.set("timestamp_ms", "" )

    end

    return [event]
end