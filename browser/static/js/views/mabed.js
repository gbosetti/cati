app.views.mabed = Backbone.View.extend({
    template: _.template($("#tpl-page-mabed").html()),
    events: {
        'submit #run_mabed': 'run_mabed',
    },
    initialize: function() {
        var handler = _.bind(this.render, this);
        this.initSpinner();
    },
    initSpinner: function(){
        /*var opts = {
          lines: 9, // The number of lines to draw
          length: 38, // The length of each line
          width: 15, // The line thickness
          radius: 32, // The radius of the inner circle
          scale: 1, // Scales overall size of the spinner
          corners: 1, // Corner roundness (0..1)
          color: '#ffffff', // CSS color or array of colors
          fadeColor: 'transparent', // CSS color or array of colors
          speed: 1, // Rounds per second
          rotate: 0, // The rotation offset
          animation: 'spinner-line-fade-quick', // The CSS animation name for the lines
          direction: 1, // 1: clockwise, -1: counterclockwise
          zIndex: 2e9, // The z-index (defaults to 2000000000)
          className: 'spinner', // The CSS class to assign to the spinner
          top: '50%', // Top position relative to parent
          left: '50%', // Left position relative to parent
          shadow: '0 0 1px transparent', // Box-shadow for the lines
          position: 'absolute' // Element positioning
        };

        this.spinner = new Spinner(opts);*/
    },
    render: function(){
        var html = this.template();
        this.$el.html(html);
        this.delegateEvents();
        console.log("Rendering the doc");
        this.getDatasetInfo();
        return this;
    },
    getDatasetInfo: function(){
        if(!app.session){
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
            //map key and doc_count to language
            console.log('is it ok ?');
            console.log(response.lang_stats);
            console.log('yes');
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
      console.log(data);
      var jc = $.confirm({
            theme: 'pix-default-modal',
            title: 'Detecting Events',
            boxWidth: '600px',
            useBootstrap: false,
            backgroundDismiss: false,
            content: 'Please Don\'t close the page until you get the success message.<br>This may take a long time (more than 10 minutes).<div class=" jconfirm-box jconfirm-hilight-shake jconfirm-type-default  jconfirm-type-animated loading" role="dialog"></div>',
            defaultButtons: false,
            buttons: {
                cancel: {
                    text: 'OK',
                    btnClass: 'btn-cancel'
                }
            }
        });
      console.log(app.appURL+'detect_events', data);
      $.post(app.appURL+'detect_events', data, function(response){
          $('#mabed_loading').fadeOut();
          jc.close();
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
            $('#mabed_loading').fadeOut();
            jc.close();
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
