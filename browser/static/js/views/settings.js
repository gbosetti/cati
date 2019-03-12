app.views.settings = Backbone.View.extend({
    template: _.template($("#tpl-page-settings").html()),
    events: {
        'submit #settings_form': 'create_session',
        'submit #session_form': 'switchSession',
        'click #deleteSession': 'deleteSession',
        'click #regenerate-ngrams': 'regenerateNgramsWithUserParams',
    },
    initialize: function() {
        this.render();
        var handler = _.bind(this.render, this);
    },
    render: function(){
        var html = this.template();
        this.$el.html(html);
        this.delegateEvents();
        this.all_sessions();
        this.show_seesion_info();
        this.update_available_indexes_list();
        app.views.mabed.prototype.getClassificationStats();

        return this;
    },
    create_session: function(e){
      e.preventDefault();
      var self = this;

      $.post(app.appURL+'add_session', $('#settings_form').serialize(), function(){
          self.all_sessions();
          self.all_sessions();
          /*self.regenerateNgrams(2, $("#session_index").val()).then(()=>{
            self.regenerateNgrams(3, $("#session_index").val());
          });*/
          $.confirm({
                title: 'Success',
                boxWidth: '600px',
                theme: 'pix-danger-modal',
                backgroundDismiss: true,
                content: "The session was successfully created.",
                buttons: {
                    Ok: {
                        btnClass: 'btn'
                    }
                }
            });

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
                        btnClass: 'btn-cancel'
                    }
                }
            });
        });
      return false;
    },
    switchSession: function(e){
      e.preventDefault();
      var self = this;
      var id = $( "#sessionsList option:selected").attr('value');
      $.post(app.appURL+'get_session',  $('#session_form').serialize(), function(response){
          if(response.result==true){
            app.session_id = response.body._id;
            app.session = response.body._source;
            self.show_seesion_info();
            localStorage.removeItem('session_id');
            localStorage.removeItem('session');
            localStorage.setItem('session_id', response.body._id);
            localStorage.setItem('session', JSON.stringify(response.body._source));
            console.log("sesssss");
            console.log(response);
            if(response.body._source.events){
                app.eventsCollection.reset();
              var collection = JSON.parse(response.body._source.events);
              console.log(collection);
              app.eventsCollection.add_json_events(collection);
            }else{
              app.eventsCollection.reset();
              localStorage.removeItem('events');
            }
          app.views.mabed.prototype.getClassificationStats();
          }
      }, 'json');
      return false;
    },
    show_seesion_info: function(){
        if(app.session){
          $('#cs_name').html(app.session.s_name);
          $('#cs_index').html(app.session.s_index);
          $('#cs_type').html(app.session.s_type);
          $('#cs_id').html(app.session_id);
        }else{
          this.all_sessions();
        }
    },
    all_sessions: function(){
      var self = this;
      $.get(app.appURL+'sessions', null, function(response){
          var html = "";
          $.each(response, function(i, s){
            if(i==0&&app.session_id==null){
              app.session_id = s._id;
              app.session = s._source;
              self.show_seesion_info();
              localStorage.removeItem('session_id');
              localStorage.removeItem('session');
              localStorage.setItem('session_id', s._id);
              localStorage.setItem('session', JSON.stringify(s._source));
            }
            if(s._id==app.session_id){
                html+= '<option selected value="'+s._id+'">'+s._source.s_name+'</option>';
            }else{
                html+= '<option value="'+s._id+'">'+s._source.s_name+'</option>';
            }
          });
          $('#sessionsList').html(html);
          self.show_seesion_info();
      }, 'json');
    },
    regenerateNgramsWithUserParams: function(evt){
        evt.preventDefault();
        evt.stopImmediatePropagation();
        this.regenerateNgrams($("#ngrams_length").val(), $("#session_index").val());
    },
    regenerateNgrams: function(ngrams_length, index){

        return new Promise((resolve, reject) => {

            var data = [
                {name: "index", value: index },  //app.session.s_index
                {name: "ngrams_length", value: ngrams_length},
                {name: "to_property", value: ngrams_length + "grams"}
            ];

            var keepAskingForLogs = true;

            setTimeout(() => {
                $.post(app.appURL+'generate_ngrams_for_index', data, function(response){
                    keepAskingForLogs = false;
                    console.log("generate_bigrams_for_index response: ", response);
                    resolve();
                }, 'json');
             }, 0); //New thread

            $.confirm({
                title:"(Re)generating " + ngrams_length + "-grams",
                columnClass: 'medium',
                content: ' \
                        Please, don\'t close this popup until the process is 100% finished. Click on "cancel" if you want to stop it. \
                        <div class="mt-3 progress"> \
                            <div id="ngrams-re-generation" class="progress-bar progress-bar-striped bg-warning progress-bar-animated" role="progressbar" style="width:0%; color:black;"> \
                              0% \
                            </div> \
                        </div>',
                buttons: {
                    Cancel: {
                        btnClass: 'btn-red',
                        action: function(){
                            console.log("Canceled...");
                        }
                    },
                    Close: {
                        btnClass: 'btn',
                        keys: ['enter', 'space']
                    },
                },
                onContentReady: function () {
                    var askForLogs = setInterval(function(){
                        $.get(app.appURL+'get_current_backend_logs', function(response){
                            //$('#logs').val(response.logs.reverse().join("\r\n"));
                            $("#ngrams-re-generation").css("width", response.percentage + "%");
                            $("#ngrams-re-generation").text(response.percentage + "%");

                            if(response && response.percentage >= 100){
                                clearInterval(askForLogs);
                            }
                        }, 'json');
                    }, 5000);
                },
            });
        });
    },
    update_available_indexes_list: function(){
        let self = this;

        $.get(app.appURL+'available_indexes', function (response) {
            //clear index list
            let selector = document.querySelector('#session_index');
            while (selector.firstChild) {
                selector.removeChild(selector.firstChild);
            }

            //add fields
            for(let i = 0; i< response.length; i++){
                let index_name = response[i];
                let option = document.createElement('option');
                option.setAttribute('value',index_name);
                option.appendChild(document.createTextNode(index_name));
                document.querySelector('#session_index').appendChild(option);
           }
        },'json');
    },
    deleteSession: function(e){
      e.preventDefault();
      var self = this;
      var jc = $.confirm({
            theme: 'pix-default-modal',
            title: 'Deleting Session',
            boxWidth: '600px',
            useBootstrap: false,
            backgroundDismiss: false,
            content: 'Please Don\'t close the page.<br>This may take several minutes.<div class=" jconfirm-box jconfirm-hilight-shake jconfirm-type-default  jconfirm-type-animated loading" role="dialog"></div>',
            defaultButtons: false,
            buttons: {
                cancel: {
                    text: 'OK',
                    btnClass: 'btn-cancel'
                }
            }
        });
      $.post(app.appURL+'delete_session', {id: app.session_id}, function(response){
          console.log( response );
          jc.close();
          self.all_sessions();
          self.all_sessions();
          app.session_id = null;
          app.session = null;
          self.show_seesion_info();
      }, 'json');
      return false;
    }
});
