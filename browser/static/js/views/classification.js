app.views.classification = Backbone.View.extend({
    template: _.template($("#tpl-classify-tweets").html()),
    initialize: function() {
        var handler = _.bind(this.render, this);
    },
    render: function(){

        var html = this.template();
        this.$el.html(html);
        this.delegateEvents();

        this.initializeSpinner();

        $( '#classification-strategies-tabs .nav-item a' ).on( 'click', function () {
            $( '#classification-strategies-tabs' ).find( 'li.active' ).removeClass( 'active' );
            $( this ).parent( 'li' ).addClass( 'active' );
        });

        document.querySelector("#start-automatic-learning").addEventListener("click", () => {
            document.querySelector("#tweet-questions").appendChild(this.spinner);
            this.loadTweetsForLearningStage();
        });

        document.querySelector("#to-learning-stage").addEventListener("click", () => {
            document.querySelector("#tweet-questions").appendChild(this.spinner);
        });

        document.querySelector("#to-al-validation-stage").addEventListener("click", () => {

            this.suggestClassification();
        });

        return this;
    },
    initializeSpinner: function(){

        this.spinner = document.createElement("div");
        this.spinner.className = "loader"; //new Spinner();
        this.spinner.style.float = "right";
    },
    loadTweetsForLearningStage: function(){

        $.get(app.appURL+'get_question_tweets_for_active_learning', function(response){

            $("#tweet-questions").html('');
            var tweetsHtml = '', ids;
            response.forEach(question => {
                // var filename = question.filename.replace(/^.*[\\\/]/, ''); // question.filename is a full path also with the file extension
                // console.log(question);
                tweetsHtml = tweetsHtml + ' <div class="card p-3 " id="' + question.data_unlabeled_index + '"> ' +
                                                '<div class="card-body"> ' +
                                                    '<p class="card-text">' + question.text + '</p> ' +
                                                   ' <p class="card-text"><i>Confidence</i>: ' + (question.confidence).toFixed(2) + '</p> ' +
                                                    '<div class=""> ' +
                                                        '<input type="checkbox" data-toggle="toggle" data-on="Confirmed" data-off="Negative" data-onstyle="success" data-offstyle="danger">' +
                                                    '</div> ' +
                                                '</div> ' +
                                            '</div>';
            })

            $("#tweet-questions").html(tweetsHtml);

            $(".card .card-body input").each(function() {
                $(this).bootstrapToggle();
                this.style.padding = "right";
            });

        }, 'json');
    },
    suggestClassification: function(){

        var questions = [];
        document.querySelectorAll(".card").forEach(question => {
            questions.push(question.id)
        });
        console.log(questions);

        $.post(app.appURL+'suggest_classification', {"form": questions} , function(response){

            console.log(response)

        }, 'json');
    }
});