require 'fileutils'

class Foolscrate < Formula
  desc ""
  homepage ""
  url 'https://github.com/alanfranz/foolscrate.git', :using => :git, :revision => 'c9ed0803a3b71df3caff7b10da19c45fb27df114'
  head 'https://github.com/alanfranz/foolscrate.git', :using => :git, :branch => 'v1dev'
  version "1.2"
  depends_on "python3"

  def install
      system "curl", "-O", "https://pypi.python.org/packages/8b/2c/c0d3e47709d0458816167002e1aa3d64d03bdeb2a9d57c5bd18448fd24cd/virtualenv-15.0.3.tar.gz"
      system "tar", "xvf", "virtualenv-15.0.3.tar.gz"
      python_interpreter = "#{HOMEBREW_PREFIX}/bin/python3"
      system "make", "install", "VIRTUALENV=#{File.expand_path('./virtualenv-15.0.3/virtualenv.py')} -p #{python_interpreter}", "PREFIX=#{prefix}/env"
      FileUtils.mkdir_p bin
      FileUtils.ln_s "../env/bin/foolscrate", "#{bin}/foolscrate"
  end

  test do
    # this currently fails because of a sandbox issue; to be fixed.
    system "#{prefix}/env/bin/run_all_tests"
  end
end
