$(function(){
    
    $('#list').click(function(){
        $('#list-show').fadeIn();
    });
    
    $('#add').click(function(){
        $('#add-show').fadeIn();
    });
    
    $('#delete').click(function(){
        $('#delete-show').fadeIn();
    });
    
    $('.close-modal').click(function(){
        $('#list-show').fadeOut();
        $('#add-show').fadeOut();
        $('#delete-show').fadeOut();
    });
    
})