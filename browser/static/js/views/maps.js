app.views.maps = Backbone.View.extend({
    template: _.template($("#tpl-map").html()),
    events: {
        'submit #settings_form': 'create_session',
        'click #deleteSession': 'deleteSession',
        'click #showClassificationOnMap': 'viewSession'
    },
    initialize: async function() {
        let handler = _.bind(this.render, this);
    },
    renderMap: function() {

        let geoJsonEndpoint="get_geo_coordinates";
        let searchEndpoint= "get_geo_polygon";
        let spaceTimeEndpoint= "get_geo_polygon_date";
        let accessToken='pk.eyJ1IjoibG9rdW11cmEiLCJhIjoiY2p3OHh3cnV0MGo4bzN5cXJtOHJ4YXZ4diJ9.lJrYN-zRUdOSP-aeKq4_Mg';

        let scope = this;
        L.MakiMarkers.accessToken = accessToken;

        scope.tweets = null;
        scope.slider = $('#maps-slider-range-vertical')[0];
        noUiSlider.create(scope.slider, {
            start: [0.2, 0.5],
            connect: true,
            direction: 'rtl',  // ltr or rtl
            orientation: 'horizontal',
            tooltips: false,
            range: {
                'min': 0,
                'max': 1
            }
        });


        console.log("Render the map");
        this.mymap = L.map('mapid').setView([45.80556348, 4.80556348], 13);

        L.tileLayer('https://api.tiles.mapbox.com/v4/{id}/{z}/{x}/{y}.png?access_token={accessToken}', {
                        attribution: 'Map data &copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a> contributors, <a href="https://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>, Imagery © <a href="https://www.mapbox.com/">Mapbox</a>',
                        maxZoom: 18,
                        id: 'mapbox.streets',
                        accessToken: accessToken
                    }).addTo(scope.mymap);
        let data = {
            "index": "geo"
        };
        // call endpoint that provides geoJson, we build this using the geo index(exists only in the workstantion)
        $.post(app.appURL+geoJsonEndpoint,data,function(response, status){
            scope.addGeoToMap(response.geo);
            scope.sliderBounds(response.min_date, response.max_date);
            scope.slider.noUiSlider.on('set', values => {
                scope.sliderUpdate(values);
            });
        });
        scope.drawnItems = new L.geoJSON();
        scope.mymap.addLayer(scope.drawnItems);
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
                edit: false,
                featureGroup: scope.drawnItems,
                remove: true
            }
        };
        let drawControl = new L.Control.Draw( options);
        scope.mymap.addControl(drawControl);

        scope.mymap.on(L.Draw.Event.CREATED, function (e) {
            //TODO: support multiple polygons and trigger the search using a button
            scope.drawnItems.clearLayers();
            scope.drawnItems.addLayer(e.layer);
            scope.search_geospatial(scope.drawnItems)
                .then(r => scope.update_from_search(r));
        });
        scope.mymap.on(L.Draw.Event.DELETED, function (e) {
            scope.drawnItems.clearLayers();
            scope.search_geospatial(scope.drawnItems)
                .then(r => scope.update_from_search(r));
        });
    },
    render: async function () {


        let html = this.template();
        this.$el.html(html);
        this.delegateEvents();
        await app.views.mabed.prototype.setSessionTopBar();
        app.views.mabed.prototype.getClassificationStats();
        this.renderMap();

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
            }).then(response => resolve(response.json()));
        });
    },
    searchSpaceTime(){

        let scope = this;
        let collection = scope.drawnItems;
        let date_range = scope.slider.noUiSlider.get();
        data = {
            index: 'geo',
            collection: collection.toGeoJSON(),
            date_min: date_range[0],
            date_max: date_range[1]
        };
        let res;
        return new Promise(function (resolve,reject) {
            fetch(app.appURL+spaceTimeEndpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify(data)
            }).then(response => resolve(response.json()) );
        });
    },
    popup(){
        return  (layer) => (layer.feature.properties.tweet.text+"</br> This tweet was created : </br>" + layer.feature.properties.tweet.created_at);
    },
    update_from_search(response){
        let scope = this;
        scope.mymap.removeLayer(scope.tweets);
        scope.addGeoToMap(response.geo);
    },
    addGeoToMap(geo){
        let scope = this;
        let mapgeo = L.geoJSON(geo, {
            pointToLayer: (g,l) => L.marker(l,{
                icon: L.MakiMarkers.icon({icon: null, color: "#00b", size:"s"})
            })
        }) .bindPopup( scope.popup());
        mapgeo.on('popupopen', scope.selectTweet(mapgeo));
        mapgeo.addTo(scope.mymap);
        scope.tweets= mapgeo;
    },
    selectTweet(lgeoJSON){
        let scope = this;
        return (e) => (scope.colorUser(e.layer.feature.properties.tweet, lgeoJSON));
    },
    colorUser(tweet,collection){
        console.log("tweets",this.tweets,'heh');
        collection.eachLayer(l => {
            if (l.feature.properties.tweet.user.id_str === tweet.user.id_str) {
                //l._icon.src = "static/images/pin-m+b00.png"
                //l._icon = L.MakiMarkers.icon({icon:null, color: "#b00"});
                //l._icon= L.Icon.Default;
                l.setIcon(L.MakiMarkers.icon({icon:null, color: "#0b0"}));
            }else{
                l.setIcon(L.MakiMarkers.icon({icon: null, color: "#00b", size:"s"}));
            }
        });
    },
    viewSession(){
        let scope =this;
        let session = "session_"+app.session.s_name;
        console.log("showing sessions");
        scope.tweets.eachLayer( l => {
            if (l.feature.properties.tweet[session] === 'confirmed') {
                l.setIcon(L.MakiMarkers.icon({icon: null, color: "#0b0"}));
            } else if (l.feature.properties.tweet[session] === 'proposed') {
                l.setIcon(L.MakiMarkers.icon({icon: null, color: "#bb0"}));
            } else if (l.feature.properties.tweet[session] === 'negative') {
                l.setIcon(L.MakiMarkers.icon({icon: null, color: "#b00"}));
            }
        });
    },
    dateFromTimestamp: timestamp => new Date(parseFloat(timestamp)).toString(),
    sliderUpdate(values){
        let scope = this;
        scope.displayDate(values[0],values[1]);
        scope.searchSpaceTime()
        .then(r => scope.update_from_search(r));
    },
    displayDate(l,u){
        let scope = this;
        let lower = document.getElementById("maps-date-lower");
        let upper = document.getElementById("maps-date-upper");
        lower.innerText= scope.dateFromTimestamp(l);
        upper.innerText= scope.dateFromTimestamp(u);
    },
    sliderBounds(min, max){
        let scope = this;
        scope.slider.noUiSlider.updateOptions({
            range: {
                'min':min ,
                'max': max
            },
            start:[min,max]
        });
        scope.displayDate(min,max);
        scope.slider.noUiSlider.set([min,max]);
    }
});
