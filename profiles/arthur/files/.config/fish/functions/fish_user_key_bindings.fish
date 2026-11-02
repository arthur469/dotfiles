function __43pr_tab_suggestion
    if commandline --showing-suggestion; and not commandline --paging-mode
        commandline -f accept-autosuggestion
    else
        commandline -f complete
    end
end

function fish_user_key_bindings
    bind tab __43pr_tab_suggestion
    # La flèche droite déplace le curseur sans accepter la suggestion.
    bind right forward-char-passive
    bind shift-tab complete-and-search
end
