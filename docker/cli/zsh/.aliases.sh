# system
alias fastfetch='fastfetch --load-config "/root/.config/fastfetch/fastfetch.jsonc" -l small'
alias btop='btop --utf-force'
alias ls='eza --icons=always --color=always --no-time --no-permissions --no-user --no-filesize --group-directories-first'
alias lst='eza --icons=always --color=always --no-time --no-permissions --no-user --no-filesize  --group-directories-first --tree --level=2'
alias lsa='eza --icons=always --color=always --no-time --no-permissions --no-user --no-filesize --all --group-directories-first'
alias cat='batcat --theme base16'
alias mkdir='mkdir -p'
alias szdir='du -sh'

# python
alias ipy='clear && ipython'
alias py='clear && python3.8'
alias pyi='python3.8 -m pip install'
alias pyinc='python3.8 -m pip install --no-cache-dir'
alias pyup='python3.8 -m pip install --upgrade'
alias pyun='python3.8 -m pip uninstall'
alias pyupip='python3.8 -m pip install --upgrade pip'
alias pyvc='python3.8 -m venv .venv && source .venv/bin/activate && pyupip'
alias pyva='source .venv/bin/activate'
alias pyf='python3.8 -m pip freeze'
alias pyfr='python3.8 -m pip freeze > requirements.txt'

# files
extract ()
{
  if [ -f "$1" ] ; then

    case $1 in
      *.tar.bz2)   tar xjf $1   ;;
      *.tar.gz)    tar xzfv $1   ;;
      *.bz2)       bunzip2 $1   ;;
      *.rar)       unrar x $1   ;;
      *.gz)        gunzip $1    ;;
      *.tar)       tar xf $1    ;;
      *.tbz2)      tar xjf $1   ;;
      *.tgz)       tar xzf $1   ;;
      *.zip)       unzip $1     ;;
      *.Z)         uncompress $1;;
      *.7z)        7z x $1      ;;
      *.deb)       ar x $1      ;;
      *.tar.xz)    tar xfv $1    ;;
      *.tar.zst)   unzstd $1    ;;
      *)           echo "'$1' cannot be extracted via ex()" ;;
    esac
  else
    echo "'$1' is not a valid file"
  fi
}