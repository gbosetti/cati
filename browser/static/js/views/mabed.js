app.views.mabed = Backbone.View.extend({
    template: _.template($("#tpl-page-mabed").html()),
    events: {
        'submit #run_mabed': 'run_mabed',
        'submit #run_tobas': 'run_tobas'
    },
    initialize: function() {
        var handler = _.bind(this.render, this);
    },
    render: async function () {
        var html = this.template();
        this.$el.html(html);
        this.delegateEvents();
        this.getDatasetInfo();
        await this.setSessionTopBar();
        this.getClassificationStats();
        return this;
    },
    getClassificationStats: function () {

        setTimeout(()=>{

            if (!app.session) {
                return this.notifyNoSession();
            }
            let data=[];
            data.push({name: "index", value: app.session.s_index});
            data.push({name: "session", value: app.session.s_name});

            $.post(app.appURL + 'produce_classification_stats', data, function (response, status) {
                console.log("Updating classification stats: ", response);

                try{
                    let total_confirmed = 0;
                    let total_negative = 0;
                    let total_proposed = 0;

                    for (let stat of response.classification_stats) {
                        if (stat.key === 'confirmed') {
                            total_confirmed = stat.doc_count;
                        } else if (stat.key === 'negative') {

                            total_negative = stat.doc_count;
                        } else if (stat.key === 'proposed') {

                            total_proposed = stat.doc_count;
                        }
                    }
                    let total = total_confirmed+total_negative+total_proposed;

                    app["lastStats"] = {
                        total: total,
                        total_confirmed: total_confirmed,
                        total_negative: total_negative,
                        total_proposed: total_proposed
                    };

                    if(total == 0)
                        proposed_width = "100";
                    else proposed_width = Math.trunc(1000*total_proposed/total)/10.0;

                    document.querySelector('#classification_confirmed').textContent = "Confirmed (" + total_confirmed + ")";
                    document.querySelector('#classification_confirmed').setAttribute("style", "width: "+Math.trunc(1000*total_confirmed/total)/10.0+"%");
                    document.querySelector('#classification_negative').textContent = "Negative (" + total_negative + ")";
                    document.querySelector('#classification_negative').setAttribute("style", "width: "+Math.trunc(1000*total_negative/total)/10.0+"%");
                    document.querySelector('#classification_proposed').textContent = "Proposed (" + total_proposed + ")";
                    document.querySelector('#classification_proposed').setAttribute("style", "width: "+ proposed_width +"%");
                    document.querySelector('#progress_classification').setAttribute("title", "Confirmed: "+total_confirmed+" , Negative: "+total_negative+", Unlabeled : "+total_proposed);
                }
                catch(err){ console.log(err); }
            }).fail(function (err) {
                console.log(err);
            });
        }, 2000);
    },
    setSessionTopBar: function() {
        if(!app.session){
            console.log("There is no session set");
        }else{
            console.log("The current session is "+app.session.s_name);
        }
        return new Promise((resolve, reject) => {
            $.get(app.appURL+'sessions', null, function(response){
                resolve(response);
            }, 'json').fail(function(response) {

                console.log(response);
                alert("Sorry, there was a problem with the sessions you are trying to retrieve. We will try to clean your local data, in case this error remains, you may have no sessions registered in the cati_sessions index (you can create them from the settings page).");
                localStorage.clear();
                sessionStorage.clear();
                //document.location.reload(true);
            });
        }).then(res => {
            //console.log("available sessions:", res);
            return this.fillAvailableSessions(res,'#session_topbar')
        })
    },
    fillAvailableSessions(response,componentSelector){
        return new Promise(resolve => {
            let html = "";
            let sessions = [];
            response.forEach((element,index) => {
                if(index == 0 && app.session_id == null){
                    app.session_id = element._id;
                    app.session = element._source;
                    localStorage.removeItem('session_id');
                    localStorage.removeItem('session');
                    localStorage.setItem('session_id', element._id);
                    localStorage.setItem('session', JSON.stringify(element._source));
                }
                sessions.push([element._source.s_name, element._id]);
            });
            sessions.sort((a,b) => (a[0]>b[0])? 1:-1);
            for(sessionTuple of sessions){
                if(sessionTuple[1]===app.session_id){
                    html+= '<option selected value="'+sessionTuple[1]+'">'+sessionTuple[0]+'</option>';
                }else{
                    html+= '<option value="'+sessionTuple[1]+'">'+sessionTuple[0]+'</option>';
                }
            }
            resolve(html);
        }).then(value => {
            $(componentSelector).html(value);
        }).then( value => {
            return app.views.settings.prototype.show_seesion_info();
        });
    },
    switchSession: function(){
        //e.preventDefault();
        var self = this;
        var id = $( "#session_topbar option:selected").attr('value');

        $.post(app.appURL+'get_session',  $('#topbar_session_form').serialize(), function(response){
            if(response.result==true){
                app.session_id = response.body._id;
                app.session = response.body._source;
                localStorage.removeItem('session_id');
                localStorage.removeItem('session');
                localStorage.removeItem('image_path')

                localStorage.setItem('image_path',response.images_folder);
                app.imagesPath = response.images_folder;
                localStorage.setItem('session_id', response.body._id);
                localStorage.setItem('session', JSON.stringify(response.body._source));

                if(response.body._source.events){
                    app.eventsCollection.reset();
                    var collection = JSON.parse(response.body._source.events);
                    app.eventsCollection.add_json_events(collection);
                }else{
                    app.eventsCollection.reset();
                    localStorage.removeItem('events');
                }
                //app.views.mabed.prototype.getClassificationStats();
                //app.views.mabed.prototype.setSessionTopBar();
                location.reload();
            }
        }, 'json');
        return false;
    },
    getDatasetInfo: function () {
        if (!app.session) {
            return this.notifyNoSession()
        }

        //Enabling the spinner
        //this.spinner.spin(document.getElementById('indexing_stats'));

        var data = $('#run_mabed').serializeArray();
        data.push({name: "index", value: app.session.s_index});

        $.post( app.appURL+'produce_dataset_stats', data, function(response, status) {
            //console.log("Data: ", response, "\nStatus: ", status);

            //On request retrieval, load the new values and stop the spinner
            document.querySelector('#total_tweets').textContent = response.total_tweets; //"20000";
            document.querySelector('#total_hashtags').textContent = response.total_hashtags;
            document.querySelector('#total_urls').textContent = response.total_urls;
            document.querySelector('#lang_total').textContent = response.total_lang;
            document.querySelector('#total_images').textContent = response.total_images;
            document.querySelector('#total_mentions').textContent = response.total_mentions;
            //map key and doc_count to language

            if(response.lang_stats.length > 0){
                for (let i=0; i<10;i++){
                    document.querySelector('#lang_'+i).textContent = response.lang_stats[i].key;
                    document.querySelector('#lang_count_'+i).textContent = response.lang_stats[i].doc_count;
                }
            }

        }).fail(function(err) {
            console.log(err)
        });
    },
    notifyNoSession: function(){

        $.confirm({
            title: 'Error',
            boxWidth: '800px',
            theme: 'pix-danger-modal',
            backgroundDismiss: true,
            content: "Error! please select a session from the settings page.",
            buttons: {
                cancel: {
                    text: 'CLOSE',
                    btnClass: 'btn-cancel',
                }
            }
        });
        return false;
    },
    showProcessingEventsPopup: function(){
        barHtml = 'Please, don\'t close the page until you get the success message.<br>This may take a long time (more than 10 minutes). ' +
			'<div class="mt-3 form-group"> ' +
                '<textarea class="form-control rounded-0" id="backend_logs" rows="10">Starting...\n</textarea> ' +
            '</div>';

        var jc = $.confirm({
            title:"Detecting Events",
            columnClass: 'extra-large',
            content: barHtml,
            buttons: {
                cancel: {
                    text: 'OK',
                    btnClass: 'btn-cancel'
                }
            }
        });
        var self = this;
        self.askForLogs = setInterval(function(){
            $.get(app.appURL+'get_backend_logs', function(response){

                response = JSON.parse(response);
                //console.log(response);

                response.forEach(log => {
                    $("#backend_logs").append(new Date(log.timestamp*1000).toLocaleTimeString("en-US") + " - " + log.content + "\n");
                });
                $("#backend_logs")[0].scrollTop = $("#backend_logs")[0].scrollHeight - $("#backend_logs").height();

            }, 'json');
        }, 7000);
        return jc;
    },
    run_mabed: function(e){
        e.preventDefault();
        if(!app.session){
          return this.notifyNoSession()
        }
      console.log("Running MABED from mabed.js...");
      $('#mabed_loading').fadeIn('slow');
      var self = this;
      var data = $('#run_mabed').serializeArray();
      data.push({name: "index", value: app.session.s_index});
      data.push({name: "session", value: app.session.s_name});

      var progressPopup = this.showProcessingEventsPopup();

      $.post(app.appURL+'detect_events', data, function(response){

          if(response.result){
              self.model.reset();
              $.each(response.events.event_descriptions, function( i, value ) {
                self.model.add_event(value[0], value[1], value[2], value[3], value[4]);
              });
              var jsonCollection = JSON.stringify(self.model.toJSON());
              var impact_dataCollection = JSON.stringify(response.events.impact_data);
              // console.log(jsonCollection);
              localStorage.removeItem('events');
              localStorage.removeItem('impact_data');
              localStorage.setItem('events', jsonCollection);
              localStorage.setItem('impact_data', impact_dataCollection);
              $.post(app.appURL+'update_session_results', {index: app.session_id, events: jsonCollection, impact_data:impact_dataCollection}, function(res){
                  console.log(res);
                   $.confirm({
                    theme: 'pix-default-modal',
                    title: 'Success',
                    boxWidth: '600px',
                    type: 'green',
                    useBootstrap: false,
                    backgroundDismiss: false,
                    content: 'Event detecting was finished successfully!',
                    defaultButtons: false,
                    buttons: {
                        cancel: {
                            text: 'OK',
                            btnClass: 'btn-cancel'
                        }
                    }
                   });
                   clearInterval(self.askForLogs);
                   progressPopup.close();
              });
          }else{
              console.log("No result");
          }

      }, 'json').fail(function() {
            $.confirm({
                title: 'Error',
                boxWidth: '600px',
                theme: 'pix-danger-modal',
                backgroundDismiss: true,
                content: "An error was encountered while connecting to the server, please try again.",
                buttons: {
                    cancel: {
                        text: 'CANCEL',
                        btnClass: 'btn-cancel',
                    }
                }
            });
        });

      return false;
    },
    run_tobas: function(e){
        e.preventDefault();
        if(!app.session){
          return this.notifyNoSession()
        }
      console.log("Running TOBAS from mabed.js...");
      var self = this;
      var   data = []
            data.push({name: "index", value: app.session.s_index});
            data.push({name: "doc_field", value: "clean-text"});  // The target field from which to consider as the tweets content
            data.push({name: "max_perc_words_by_topic", value: $("#max_perc_words_by_topic").val()});
      //data.push({name: "session", value: app.session.s_name});

      //var progressPopup = this.showProcessingEventsPopup();

      $.post(app.appURL+'detect_events_with_tobas', data, function(response){

         console.log("RESPONSE FROM TOBAS", data);

      }, 'json').fail(function() {
            $.confirm({
                title: 'Error',
                boxWidth: '600px',
                theme: 'pix-danger-modal',
                backgroundDismiss: true,
                content: "An error was encountered while connecting to the server, please try again.",
                buttons: {
                    cancel: {
                        text: 'CANCEL',
                        btnClass: 'btn-cancel',
                    }
                }
            });
        });

      return false;
    }
});