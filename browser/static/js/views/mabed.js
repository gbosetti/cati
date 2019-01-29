app.views.mabed = Backbone.View.extend({
    template: _.template($("#tpl-page-mabed").html()),
    events: {
        'submit #run_mabed': 'run_mabed',
    },
    initialize: function() {
        var handler = _.bind(this.render, this);
    },
    render: function(){
        var html = this.template();
        this.$el.html(html);
        this.delegateEvents();
        return this;
    },
    run_mabed: function(e){
      e.preventDefault();
        if(!app.session){
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
      }
      console.log("Running MABED...");
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
