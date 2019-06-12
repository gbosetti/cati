let geoJsonEndpoint="get_geo_coordinates";
let searchEndpoint= "get_geo_polygon";
let accessToken='pk.eyJ1IjoibG9rdW11cmEiLCJhIjoiY2p3OHh3cnV0MGo4bzN5cXJtOHJ4YXZ4diJ9.lJrYN-zRUdOSP-aeKq4_Mg';
app.views.maps = Backbone.View.extend({
    template: _.template($("#tpl-map").html()),
    events: {
        'submit #settings_form': 'create_session',
        'click #deleteSession': 'deleteSession',
        'click #regenerate-ngrams': 'regenerateNgramsWithUserParams',
    },
    initialize: async function() {
        let handler = _.bind(this.render, this);
    },
    render: async function () {
        let scope = this;
        let html = this.template();
        this.$el.html(html);
        this.delegateEvents();
        await app.views.mabed.prototype.setSessionTopBar();
        app.views.mabed.prototype.getClassificationStats();
        let tweets = null;

        console.log("Render the map");
        let mymap = L.map('mapid').setView([45.80556348, 4.80556348], 13);

        L.tileLayer('https://api.tiles.mapbox.com/v4/{id}/{z}/{x}/{y}.png?access_token={accessToken}', {
                        attribution: 'Map data &copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a> contributors, <a href="https://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>, Imagery © <a href="https://www.mapbox.com/">Mapbox</a>',
                        maxZoom: 18,
                        id: 'mapbox.streets',
                        accessToken: accessToken
                    }).addTo(mymap);
        let data = {
            "index": "geo"
        };
        // call endpoint that provides geoJson, we build this using the geo index(exists only in the workstantion)
        $.post(app.appURL+geoJsonEndpoint,data,function(response, status){
            console.log(response);
            tweets = L.geoJson(response).bindPopup( scope.popup());
            tweets.on('popupopen', scope.selectTweet(tweets));
            tweets.addTo(mymap);
        });
        let drawnItems = new L.geoJSON();
        mymap.addLayer(drawnItems);
        let options = {
            position: 'topright',
            draw: {
                polyline: false,
                marker: false,
                layer: false,
                circlemarker: false,
                polygon: {
                    allowIntersection: false,
                    drawError: {
                        color: '#e1e100',
                        message: '<strong> Wrong shape </strong>'
                    },
                    shapeOptions: {
                        color:'#3be'
                    }
                },
                circle: false,
                rectangle: {
                    shapeOptions: {
                        color:'#3be'
                    }
                },
            },
            edit: {
                edit: true,
                featureGroup: drawnItems,
                remove: true
            }
        };
        let drawControl = new L.Control.Draw( options);
        mymap.addControl(drawControl);

        mymap.on(L.Draw.Event.CREATED, function (e) {
            //TODO: support multiple polygons and trigger the search using a button
            drawnItems.clearLayers();
            drawnItems.addLayer(e.layer);
            scope.search_geospatial(drawnItems)
                .then(nt => {
                    console.log("newtweets");
                    console.log(nt);
                    mymap.removeLayer(tweets);
                    nt.addTo(mymap);
                    tweets= nt;
                });
        });
        return this;
    },
    search_geospatial(collection){
        let scope = this;
        data = {
            index: 'geo',
            collection: collection.toGeoJSON(),
        };
        let res;
        return new Promise(function (resolve,reject) {
            fetch(app.appURL+searchEndpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify(data)
            }).then(response => response.json())
            .then(response => {
                // still must update the results
                let res = L.geoJSON(response) .bindPopup( scope.popup());
                    res.on('popupopen', scope.selectTweet(res));
                resolve(res);
            });
        });

    },
    popup(){
        return  (layer) => (layer.feature.properties.tweet.text+"</br> This tweet was created : </br>" + layer.feature.properties.tweet.created_at);
    },
    selectTweet(lgeoJSON){
        console.log('my collection',lgeoJSON);
        let scope = this;
        return (e) => (scope.colorUser(e.layer.feature.properties.tweet, lgeoJSON));
    },
    colorUser(tweet,collection){
        L.MakiMarkers.accessToken = accessToken;
        collection.eachLayer(l => {
            if (l.feature.properties.tweet.user.id_str === tweet.user.id_str) {
                //l._icon.src = "static/images/pin-m+b00.png"
                //l._icon = L.MakiMarkers.icon({icon:null, color: "#b00"});
                //l._icon= L.Icon.Default;
                l.setIcon(L.MakiMarkers.icon({icon:null, color: "#b00"}));
                console.log(l);
            }else{
                l.setIcon(L.MakiMarkers.icon({icon: null, color: "#0b0"}));
            }
        });
    },

});
