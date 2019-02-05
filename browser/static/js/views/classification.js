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

        this.loadTweetsForLearningStage();

        return this;
    },
    loadTweetsForLearningStage: function(){

        $.get(app.appURL+'get_question_tweets_for_active_learning', function(response){

            console.log("RESPONSE", response)
            var tweetsHtml = 'Hola!'

            $("#tweets-to-mark-for-learning").html(tweetsHtml)
        }, 'json');


    }
});