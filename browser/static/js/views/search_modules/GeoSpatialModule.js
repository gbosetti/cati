class GeoSpatialModule extends SearchModule{

    constructor(containerSelector, client) {

        super(containerSelector);

        this.client = client;
        this.accessToken='pk.eyJ1IjoibG9rdW11cmEiLCJhIjoiY2p3OHh3cnV0MGo4bzN5cXJtOHJ4YXZ4diJ9.lJrYN-zRUdOSP-aeKq4_Mg';
        this.tweets = null;
        $( "#collapseGeopositioned" ).on( "click", ".onTweetStatusClicked", (evt)=>{
            this.geo_document_to_state(evt);
        });
        $( ".geo_selection_to_state" ).on( "click", (evt)=>{
            this.geo_selection_to_state(evt);
        });
        this.lastZoomAt = null;
    }
    geo_selection_to_state(evt){

        evt.preventDefault();
        var jc = this.client.createChangingStatePopup();

        var tweetsIds = this.loadedDocuments.map(doc => { return doc.properties.doc_id});
        if(tweetsIds.length>0){

            var data = this.client.getIndexAndSession();
                data.push({name: "state", value: $(evt.target).data("state")});
                data.push({name: "docs_ids", value: tweetsIds});

            $.post(app.appURL+'geo_selection_to_state', data, function(response){
                app.views.mabed.prototype.getClassificationStats();
                jc.close();
            }, 'json').fail(this.client.cnxError);
        }

        return false;
    }
    geo_document_to_state(evt){
        evt.preventDefault();

        var tweetId = $(evt.target).data("doc-id");
        if(tweetId != undefined && tweetId != null){

            var data = this.client.getIndexAndSession();
                data.push({name: "val", value: $(evt.target).data("status")});
                data.push({name: "tid", value: tweetId});

            $.post(app.appURL + 'mark_tweet', data, function(response){
                app.views.mabed.prototype.getClassificationStats();
                 $(".leaflet-popup-close-button")[0].click();
            }, 'json').fail(this.client.cnxError);

        }

        return false;
    }
    search_geospatial(collection, data){

        let date_range = this.slider.noUiSlider.get();
        var geo_data = {
            "index": app.session.s_index,
            "session": 'session_'+app.session.s_name,
            "collection": collection.toGeoJSON(),
            "search_by_label": data.filter(item => {return item.name == "search_by_label"})[0].value,
            "word": data.filter(item => {return item.name == "word"})[0].value,
            "date_min": date_range[0],
            "date_max": date_range[1]
        };
        return new Promise(function (resolve,reject) {

            fetch(app.appURL+"get_geo_polygon", {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify(geo_data)
            }).then(response => resolve(response.json()));
        });
    }
    searchSpaceTime(data){

        let collection = this.drawnItems;
        let date_range = this.slider.noUiSlider.get();
        var data = {
            index: app.session.s_index,
            session: 'session_'+app.session.s_name,
            search_by_label: data.filter(item => {return item.name == "search_by_label"})[0].value,
            word: data.filter(item => {return item.name == "word"})[0].value,
            collection: collection.toGeoJSON(),
            date_min: date_range[0],
            date_max: date_range[1]
        };
        return new Promise(function (resolve,reject) {
            let spaceTimeEndpoint= "get_geo_polygon_date";
            fetch(app.appURL+spaceTimeEndpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify(data)
            }).then(response => resolve(response.json()) );
        });
    }
    popup(){
        return  (layer) => (
            layer.feature.properties.tweet.text +
            '</br></br><b>Created on:</b> ' + this.formatDateFromString(layer.feature.properties.tweet.created_at) +
            '</br></br><div style="display: flex; justify-content: flex-end;">'+
                '<button data-doc-id="' + layer.feature.properties.doc_id + '" data-status="confirmed" class="onTweetStatusClicked" style="background: rgba( 40, 167, 69, 0.5);">Confirm</button>'+
                '<button data-doc-id="' + layer.feature.properties.doc_id + '" data-status="negative" class="onTweetStatusClicked" style="background: rgba(220, 53, 69, 0.63);">Reject</button>' +
                '<button data-doc-id="' + layer.feature.properties.doc_id + '" data-status="unlabeled" class="onTweetStatusClicked">Clear</button>'+
            '</div>' //+ this.createButton('Confirm')
        );
    }
    createButton(label) {
        var btn = L.DomUtil.create('button');
        btn.setAttribute('type', 'button');
        btn.innerHTML = label;
        return btn;
    }
    update_from_search(response){
        this.mymap.removeLayer(this.tweets);
        this.addGeoToMap(response.geo);
    }
    addGeoToMap(geo){
        this.loadedDocuments = geo;
        let mapgeo = L.geoJSON(geo, {
            pointToLayer: (g,latlng) => L.marker(latlng,{
                icon: L.MakiMarkers.icon({icon: null, color: "#00b", size:"s"})
            })
        }).bindPopup(this.popup());
        mapgeo.on('popupopen', this.selectTweet(mapgeo));
        mapgeo.addTo(this.mymap);
        this.tweets= mapgeo;
    }
    selectTweet(lgeoJSON){
        return (e) => (this.colorUser(e.layer.feature.properties.tweet, lgeoJSON));
    }
    colorUser(tweet,collection){
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
    }
    viewSession(){
        let session = "session_"+app.session.s_name;
        this.tweets.eachLayer( l => {
            if (l.feature.properties.tweet[session] === 'confirmed') {
                l.setIcon(L.MakiMarkers.icon({icon: null, color: "#0b0"}));
            } else if (l.feature.properties.tweet[session] === 'proposed') {
                l.setIcon(L.MakiMarkers.icon({icon: null, color: "#bb0"}));
            } else if (l.feature.properties.tweet[session] === 'negative') {
                l.setIcon(L.MakiMarkers.icon({icon: null, color: "#b00"}));
            }
        });
    }
    dateFromTimestamp(timestamp){
        var fecha = new Date(parseFloat(timestamp));
        return fecha.toLocaleDateString() + " " + fecha.toLocaleTimeString()
    }
    formatDateFromString(aStringDate){

        var aDate = new Date(aStringDate);
        return aDate.toLocaleDateString() + " " + aDate.toLocaleTimeString()
    }
    sliderUpdate(extremeDates, data){
        //this.enableLoading("#mapid");
        this.displayDate(extremeDates[0],extremeDates[1]);
        this.searchSpaceTime(data)
        .then(r => {
            this.update_from_search(r);
            this.updateMatchingTweetsLabel(r.total_hits, r.geo.length);
            //this.disableLoading("#mapid");
        });
    }
    displayDate(lowerDate,upperDate){
        let lower = document.getElementById("maps-date-lower");
        let upper = document.getElementById("maps-date-upper");

        if(lower != null) lower.innerText= this.dateFromTimestamp(lowerDate);
        if(upper != null) upper.innerText= this.dateFromTimestamp(upperDate);
    }
    sliderBounds(min, max, skipUpdate = false){
        this.slider.noUiSlider.updateOptions({
            range: {
                'min':min ,
                'max': max
            },
            start:[min,max]
        });
        this.displayDate(min,max);
        if (skipUpdate == false){
            this.slider.noUiSlider.set([min,max]);
        }
    }
    loadSlider(){

        this.slider = $('#maps-slider-range-vertical')[0];
        noUiSlider.create(this.slider, {
            start: [0, 1],
            connect: true,
            direction: 'ltr',  // ltr or rtl
            orientation: 'horizontal',
            tooltips: false,
            range: { 'min': 0, 'max': 1 }
        });
        this.slider.noUiSlider.on('set', values => {
            if(this.slider_data)
                this.sliderUpdate(values, this.slider_data);
        });
    }
    loadTweets(data){


        return new Promise((resolve, reject)=>{

            L.MakiMarkers.accessToken = this.accessToken;
            this.loadSlider();
            this.mymap = L.map('mapid');

            var mapLayer = L.tileLayer('https://api.tiles.mapbox.com/v4/{id}/{z}/{x}/{y}.png?access_token={accessToken}', {
                            attribution: 'Map data &copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a> contributors, <a href="https://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>, Imagery © <a href="https://www.mapbox.com/">Mapbox</a>',
                            maxZoom: 18,
                            id: 'mapbox.streets',
                            accessToken: this.accessToken
                        }).addTo(this.mymap);

            this.drawnItems = new L.geoJSON();
            this.mymap.addLayer(this.drawnItems);
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
                    featureGroup: this.drawnItems,
                    remove: true
                }
            };
            let drawControl = new L.Control.Draw( options);
            this.mymap.addControl(drawControl);

            this.mymap.on(L.Draw.Event.CREATED, (e) => {
                //TODO: support multiple polygons and trigger the search using a button
                this.enableLoading();
                this.drawnItems.clearLayers();
                this.drawnItems.addLayer(e.layer);
                this.search_geospatial(this.drawnItems, data)
                    .then(r => {
                        this.update_from_search(r);
                        this.updateMatchingTweetsLabel(r.total_hits, r.geo.length);
                        this.disableLoading("#mapid");
                    });
            });
            this.mymap.on(L.Draw.Event.DELETED, (e) => {
                this.drawnItems.clearLayers();
                this.search_geospatial(this.drawnItems, data)
                    .then(r => {
                        this.updateMatchingTweetsLabel(r.total_hits, r.geo.length);
                        this.update_from_search(r);
                    });
            });

            // call endpoint that provides geoJson, we build this using the geo index(exists only in the workstantion)
            var spec_data = {
                "index": app.session.s_index,
                "session": 'session_'+app.session.s_name,
                "search_by_label": data.filter(item => {return item.name == "search_by_label"})[0].value,
                "word": data.filter(item => {return item.name == "word"})[0].value
            };

            this.searchGeoLocalizedTweets(spec_data, data).then(()=>{

                console.log("Done!")
                /*this.mymap.on('zoomstart', ()=>{
                    clearTimeout(this.timeoutID);
                    //this.lastZoomAt = Date.now();
                });
                this.mymap.on('zoomend', (evt)=>{

                    //console.log(Date.now()-this.lastZoomAt);
                    this.timeoutID = setTimeout(()=>{
                        clearTimeout(this.timeoutID);
                        this.searchGeoLocalizedTweets(spec_data, data, false);
                    },2000);
                });
                //this.mymap.on('zoom', ()=>{ console.log("zoom") });*/

                /*this.mymap.on('zoomend', ()=>{
                    this.enableLoading();

                        console.log("ZOOMING + LOADING!");
                        this.searchGeoLocalizedTweets(spec_data, data).then(()=>{
                            this.disableLoading();
                        });
                });*/
            });
        });
    }
    setLastZoomAt(val){
        this.lastZoomAt = val;
    }
    getLastZoomAt(){
        return this.lastZoomAt;
    }
    searchGeoLocalizedTweets(spec_data, slider_data, fitBounds = true){

        return new Promise((resolve, reject)=>{

            this.enableLoading();
            $.post(app.appURL+"get_geo_coordinates", spec_data ,(response, status) => {

                if (response.geo.length > 0){
                    // Update map
                    this.addGeoToMap(response.geo);
                    var markerArray = response.geo.map(pdi => L.marker(pdi.geometry.coordinates));
                    var group = L.featureGroup(markerArray); //.addTo(map);

                    if(fitBounds){
                        this.mymap.setView(this.tweets.getBounds().getCenter(),1).fitBounds(this.tweets.getBounds());
                        console.log("Fitting bounds");
                    }
                    else{
                        console.log("BOUNDS:", this.mymap.getBounds());
                    }

                    // Update slider
                    this.slider_data = slider_data;

                    if(response.min_date == response.max_date){
                        $(".maps-slider-area").html("");
                    }
                    else this.sliderBounds(response.min_date, response.max_date, true);

                    // Updating query info section
                    this.updateMatchingTweetsLabel(response.total_hits, response.geo.length);
                    this.disableLoading();
                }
                else this.showNoTweetsFound()
                resolve();
            });
        });
    }
    updateMatchingTweetsLabel(numOfFoundTweets, numOfRetrievedTweets){
        $(".geo_tweets_results").html(numOfFoundTweets + ' results matching the query (showing ' + numOfRetrievedTweets + ')');
    }
    showNoTweetsFound(){
        $(this.containerSelector).parent().html("Sorry, no geo-localized tweets were found under this criteria.");
    }
}