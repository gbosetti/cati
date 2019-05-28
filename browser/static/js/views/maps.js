app.views.maps = Backbone.View.extend({
    template: _.template($("#tpl-map").html()),
    events: {
        'submit #settings_form': 'create_session',
        'click #deleteSession': 'deleteSession',
        'click #regenerate-ngrams': 'regenerateNgramsWithUserParams',
    },
    initialize: async function() {

        var handler = _.bind(this.render, this);
    },
    render: async function () {
        var html = this.template();
        this.$el.html(html);
        this.delegateEvents();
        await app.views.mabed.prototype.setSessionTopBar();
        app.views.mabed.prototype.getClassificationStats();

        console.log("Render the map");
        var mymap = L.map('mapid').setView([51.505, -0.09], 13);

        L.tileLayer('https://api.tiles.mapbox.com/v4/{id}/{z}/{x}/{y}.png?access_token={accessToken}', {
            attribution: 'Map data &copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a> contributors, <a href="https://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>, Imagery © <a href="https://www.mapbox.com/">Mapbox</a>',
            maxZoom: 18,
            id: 'mapbox.streets',
            accessToken: 'your.mapbox.access.token'
        }).addTo(mymap);
        return this;
    }

});
