let geoJsonEndpoint="get_geo_coordinates";
let searchEndpoint= "get_geo_polygon";
let spaceTimeEndpoint= "get_geo_polygon_date";
let accessToken='pk.eyJ1IjoibG9rdW11cmEiLCJhIjoiY2p3OHh3cnV0MGo4bzN5cXJtOHJ4YXZ4diJ9.lJrYN-zRUdOSP-aeKq4_Mg';
L.MakiMarkers.accessToken = accessToken;

/*let mapPopup = (options)  =>{
    Backbone.View.apply(this, arguments);
    this.popup = new L.Popup(options)
};
mapPopup.extend = Backbone.view.extend;
_.extend( mapPopup.prototype, Backbone.View.prototype){
    constructor: mapPopup()
};*/

let popup = Backbone.View.extend({
    constructor: ()=> {
        Backbone.View.apply(this, arguments);
        this.popup = new L.Popup(options)
    },

    template: _.template("<%= properties.tweet.text %></br> This tweet was created : </br> <%= properties.tweet.created_at %>"),
    render: () => {
        if(this.popup._content !== this.el){
            this.popup.setContent(this.el);
        }
        this.$el.html(this.template(this.model.toJSON()))
        return this;
    },

    setModel: model => {
        if (model){
            if( this.model ){
                this.stopListening( this.model );
            }
            this.model = model;
            this.listenTo(model, 'change', this.render());
        }
    }
});

app.views.maps = Backbone.View.extend({
    template: _.template($("#tpl-map").html()),
    events: {
        'click #showClassificationOnMap': 'viewSession'
    },
    preinitialize: function(){
        let scope = this;
        let html = this.template();
        this.$el.html(html);
    },
    initialize: async function() {
        await console.log(this);
        await this._ensureMap();
        this._initDrawControl();

        this.tweets = this._getLayer();
        this.tweets.addTo(this.map);

        if (this.collection) {
            if (!(this.collections instanceof app.collections.events)) {
                throw new Error( 'The "collection" option should be instance of '+ app.collections.events +'to be used within Map view');
            }

            // Bind Collection events.
            this.listenTo( this.collection, 'reset', this._onReset );
            this.listenTo( this.collection, 'add', this._onAdd );
            this.listenTo( this.collection, 'remove', this._onRemove );
            this.listenTo( this.collection, 'change', this._onChange );
            this.redraw();
        }
        this.listenTo(this.model, 'change', this.render);
        let handler = _.bind(this.render, this);
    },
    render: async function () {
        let scope = this;
        scope.map.invalidateSize();
        this.delegateEvents();
        await app.views.mabed.prototype.setSessionTopBar();
        app.views.mabed.prototype.getClassificationStats();
        scope.tweets = null;

        scope.slider = $('#maps-slider-range-vertical')[0];

        noUiSlider.create(scope.slider, {
            start: [0.2, 0.5],
            connect: true,
            direction: 'rtl',  // ltr or rtl
            orientation: 'vertical',
            tooltips: false,
            range: {
                'min': 0,
                'max': 1
            }
        });

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



        return this;
    },
    redraw: () => {
        this._layers = {};
        this.tweets.clearLayers();
        this.tweets.addData(this.collection.toJSON({cid: true}));
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
        scope.map.removeLayer(scope.tweets);
        scope.addGeoToMap(response.geo);
    },
    addGeoToMap(geo){
        let scope = this;
        let mapgeo = L.geoJSON(geo, {
            pointToLayer: (point,LatLng) => L.marker(LatLng,{
                icon: L.MakiMarkers.icon({icon: null, color: "#00b", size:"s"})
            }),
            style: feature => {
                color: "#00b";
            }
        }) .bindPopup( scope.popup());
        mapgeo.on('popupopen', scope.selectTweet(mapgeo));
        mapgeo.addTo(scope.map);
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
    },
    _ensureMap:function(){
        console.log('ensure',this);
        let scope = this;
        return new Promise((resolve,reject)=> {
            if (scope.map != undefined) {
                resolve(scope);
            }else {
                scope.map = L.map('mapid').setView([45.80556348, 4.80556348], 13);

                scope.tileLayer = L.tileLayer('https://api.tiles.mapbox.com/v4/{id}/{z}/{x}/{y}.png?access_token={accessToken}', {
                    attribution: 'Map data &copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a> contributors, <a href="https://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>, Imagery © <a href="https://www.mapbox.com/">Mapbox</a>',
                    maxZoom: 18,
                    id: 'mapbox.streets',
                    accessToken: accessToken
                });
                scope.tileLayer.addTo(scope.map);
                resolve(scope);
            }
        });
    },
    _initDrawControl: function() {
        let scope = this;
        scope.drawnItems = new L.geoJSON();
        scope.map.addLayer(scope.drawnItems);
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
        scope.map.addControl(drawControl);
                scope.map.on(L.Draw.Event.CREATED, function (e) {
            //TODO: support multiple polygons and trigger the search using a button
            scope.drawnItems.clearLayers();
            scope.drawnItems.addLayer(e.layer);
            scope.search_geospatial(scope.drawnItems)
                .then(r => scope.update_from_search(r));
        });
        scope.map.on(L.Draw.Event.DELETED, function (e) {
            scope.drawnItems.clearLayers();
            scope.search_geospatial(scope.drawnItems)
                .then(r => scope.update_from_search(r));
        });
    },
    _getLayer: (geo) => {
        let scope = this;
        let mapgeo = L.geoJSON(geo, {
            pointToLayer: (point,LatLng) => L.marker(LatLng,{
                icon: L.MakiMarkers.icon({icon: null, color: "#00b", size:"s"})
            }),
            style: feature => {
                color: "#00b";
            }
        }) .bindPopup( scope.popup());
        mapgeo.on('popupopen', scope.selectTweet(mapgeo));
        return mapgeo;
    }
});
