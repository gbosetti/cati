app.views.mabed = Backbone.View.extend({
    template: _.template($("#tpl-page-mabed").html()),
    events: {
        'submit #run_mabed': 'run_mabed',
    },
    initialize: function() {
        var handler = _.bind(this.render, this);
        this.keepaskingForLogs = false;
    },
    render: function () {
        var html = this.template();
        this.$el.html(html);
        this.delegateEvents();
        console.log("Rendering the doc");
        this.getDatasetInfo();
        return this;
    },
    getClassificationStats: function () {
        if (!app.session) {
            return this.notifyNoSession();
        }
        var data = $('#run_mabed').serializeArray();
        data.push({name: "index", value: app.session.s_index});
        data.push({name: "session", value: app.session.s_name});

        $.post(app.appURL + 'produce_classification_stats', data, function (response, status) {
            //console.log("Updating classification stats: ", response);
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

            document.querySelector('#classification_confirmed').textContent = "Confirmed (" + total_confirmed + ")";
            document.querySelector('#classification_confirmed').setAttribute("style", "width: "+Math.trunc(1000*total_confirmed/total)/10.0+"%");
            document.querySelector('#classification_negative').textContent = "Negative (" + total_negative + ")";
            document.querySelector('#classification_negative').setAttribute("style", "width: "+Math.trunc(1000*total_negative/total)/10.0+"%");
            document.querySelector('#classification_proposed').textContent = "Proposed (" + total_proposed + ")";
            document.querySelector('#classification_proposed').setAttribute("style", "width: "+Math.trunc(1000*total_proposed/total)/10.0+"%");
            document.querySelector('#progress_classification').setAttribute("title", "Confirmed: "+total_confirmed+
                " , Negative: "+total_negative+", Unlabeled : "+total_proposed);
            app.views.mabed.prototype.setSessionTopBar();
        }).fail(function (err) {
            console.log(err);
        });
    },
    setSessionTopBar: function() {
        console.log("The current session is "+app.session.s_name);
        document.querySelector('#current_session').textContent = app.session.s_name;
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
            console.log( "success" );
            console.log("Data: ", response, "\nStatus: ", status);

            //On request retrieval, load the new values and stop the spinner
            document.querySelector('#total_tweets').textContent = response.total_tweets; //"20000";
            document.querySelector('#total_hashtags').textContent = response.total_hashtags;
            document.querySelector('#total_urls').textContent = response.total_urls;
            document.querySelector('#lang_total').textContent = response.total_lang;
            document.querySelector('#total_images').textContent = response.total_images;
            document.querySelector('#total_mentions').textContent = response.total_mentions;
            //map key and doc_count to language
            for (let i=0; i<10;i++){
                document.querySelector('#lang_'+i).textContent = response.lang_stats[i].key;
                document.querySelector('#lang_count_'+i).textContent = response.lang_stats[i].doc_count;
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
        this.keepaskingForLogs = true;
        var askForLogs = setInterval(function(){
            $.get(app.appURL+'get_backend_logs', function(response){

                response.forEach(log => {
                    $("#backend_logs").append(new Date(log.timestamp*1000).toLocaleTimeString("en-US") + " - " + log.content + "\n");
                });
                $("#backend_logs")[0].scrollTop = $("#backend_logs")[0].scrollHeight - $("#backend_logs").height();

                if(self.keepaskingForLogs == false){
                    clearInterval(askForLogs);
                }
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

      this.showProcessingEventsPopup();

      $.post(app.appURL+'detect_events', data, function(response){

          self.keepaskingForLogs = false;

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
    }
});