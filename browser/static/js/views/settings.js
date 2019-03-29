app.views.settings = Backbone.View.extend({
    template: _.template($("#tpl-page-settings").html()),
    events: {
        'submit #settings_form': 'create_session',
        'submit #session_form': 'switchSession',
        'click #deleteSession': 'deleteSession',
        'click #regenerate-ngrams': 'regenerateNgramsWithUserParams',
    },
    initialize: async function() {

        var html = this.template();
        this.$el.html(html);
        this.delegateEvents();
        await app.views.mabed.prototype.setSessionTopBar();
        this.all_sessions();
        this.show_seesion_info();
        this.update_available_indexes_list();

        return this;
    },
    showProcessingEventsPopup: function(popupTitle){
        barHtml = 'Please, don\'t close the page until you get the success message.<br>This may take a long time (more than 10 minutes). ' +
               '<div class="mt-3 progress"> ' +
           '<div id="session-creation-progress" class="progress-bar" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100" role="progressbar" style="width:0%"> ' +
            '  0% ' +
           ' </div> ' +
          '</div>';
          			//'<div lclass="mt-3 form-group"> ' +
                //'<textarea class="form-control rounded-0" id="backend_logs" rows="10">Starting...\n</textarea> ' +
           // '</div>';

        var jc = $.confirm({
            title:popupTitle,
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
            $.post(app.appURL+'get_elastic_logs', [{name: "index", value: app.session.s_index}], function(response){

                if (response["nodes"] == undefined || Object.keys(response["nodes"]).length == 0)
                    return;

                var taskIndex = Object.keys(response["nodes"])[0];
                var taskIndexWithProc = Object.keys(response["nodes"][taskIndex]['tasks'])[0];
                var task = response["nodes"][taskIndex]['tasks'][taskIndexWithProc];
                var accum = (task.status.updated * 100 / task.status.total).toFixed(0);

                $("#session-creation-progress").text(accum + "%");
                $("#session-creation-progress").css("width", accum + "%");

            }, 'json');
        }, 7000);
        return jc;
    },
    create_session: function(e){
      e.preventDefault();
      var self = this;

      if ($('#session_name').val() == undefined || $('#session_name').val().trim() == ""){
        alert("Please, choose a name for the session and try again.");
        return;
      }

      var processingPopup = this.showProcessingEventsPopup('Creating Session');

      $.post(app.appURL+'add_session', $('#settings_form').serialize(), function(){

          self.all_sessions();

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
          clearInterval(self.askForLogs);
          processingPopup.close()

      }, 'json').fail(function(err) {
            $.confirm({
                title: 'Error',
                boxWidth: '600px',
                theme: 'pix-danger-modal',
                backgroundDismiss: true,
                content: "An error was encountered while connecting to the server. Please, try again.",
                buttons: {
                    cancel: {
                        text: 'CANCEL',
                        btnClass: 'btn-cancel'
                    }
                }
            });
            console.log(err);
            clearInterval(self.askForLogs);
        });
      return false;
    },
    switchSession: function(e){
      e.preventDefault();
      var self = this;
      var id = $( "#sessionsList option:selected").attr('value');
      $.post(app.appURL+'get_session',  $('#session_form').serialize(), async function(response){
          if(response.result==true){
            app.session_id = response.body._id;
            app.session = response.body._source;
            self.show_seesion_info();
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
          await app.views.mabed.prototype.setSessionTopBar();
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
        } //else { this.all_sessions(); }
    },
    all_sessions: function(){
        let self =this;
        return new Promise(resolve => {
            $.get(app.appURL+'sessions', null, function(response){
                resolve(response);
            }, 'json');
        }).then(value => {
            return self.handleSessions(value,'#sessionsList')
        })
    },
    handleSessions(response,componentSelector){
        var self = this;
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
            return self.show_seesion_info();
        });
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
          app.session_id = null;
          app.session = null;
          self.show_seesion_info();
      }, 'json');
      return false;
    }
});
