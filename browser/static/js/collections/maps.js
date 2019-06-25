let mapsEndpoint = "/maps";
app.collections.maps = Backbone.Collection.extend({

    model: app.models.map_tweet,

    url: mapsEndpoint,

    parse: data => data.geo,

    //TODO: the same for negative and unlabeled
    confirmed: () => {
        let session = "session_"+app.session.s_name;
        attrs = {};
        Object.defineProperty(attrs, session, {
            value: "Confirmed",
            writable: false
        });
        this.where(attrs);
    },

    toJSON: (options) => {
        let features = Backbone.Collection.prototype.toJSON.apply(this, arguments);
        return {
            type: 'FeatureCollection',
            features: features
        };
    }


});
