app.views.classification = Backbone.View.extend({
    template: _.template($("#tpl-classify-tweets").html()),
    initialize: function() {
        var handler = _.bind(this.render, this);
    },
    render: function(){

        console.log("Rendering view")
        var html = this.template();
        this.$el.html(html);
        this.delegateEvents();

        return this;
    }
});