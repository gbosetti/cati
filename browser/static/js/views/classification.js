app.views.classification = Backbone.View.extend({
    template: _.template($("#tpl-classify-tweets").html()),
    initialize: function() {
        var handler = _.bind(this.render, this);
    },
    render: function(){

        var html = this.template();
        this.$el.html(html);
        this.delegateEvents();

        $( '#classification-strategies-tabs .nav-item a' ).on( 'click', function () {
            $( '#classification-strategies-tabs' ).find( 'li.active' ).removeClass( 'active' );
            $( this ).parent( 'li' ).addClass( 'active' );
        });

        document.querySelector("#start-automatic-learning").addEventListener("click", () => {
            this.loadTweetsForLearningStage();
        });

        return this;
    },
    loadTweetsForLearningStage: function(){

        $.get(app.appURL+'get_question_tweets_for_active_learning', function(response){

            $("#tweet-questions").html('');
            var tweetsHtml = '', ids;
            response.forEach(question => {
                console.log(question.confidence);
                tweetsHtml = tweetsHtml + ' <div class="card p-3 "> ' +
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
    }
});