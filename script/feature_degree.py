# -*- coding:utf-8 -*-

from version import *
from common_num import *
import json
import numpy as np

def make_feat(inpath,outpath,isTrain=True):
    fin,fout=open(inpath),open(outpath,"w")

    fout.write("id,major,gender,first_work_age,first_industry,first_size,first_salary,first_poslevel,"
               "total_worktime_per_work,total_worktime_per_industry,average_salary,firstmaxposworktime,"
               "salary_in_major_level,salary_in_industry_level,salary_in_position_level")
    if isTrain:
        fout.write(",ydegree\n")
    else:
        fout.write("\n")

    samples=fin.readlines()
    fin.close()

    major_salary,industry_salary,position_salary={},{},{}

    # get 3 kinds of salary percentile
    for sample in samples:
        jsonobj=json.loads(sample)
        wn=len(jsonobj["workExperienceList"])
        # if train, but work experience less than 3
        if isTrain and wn<3: continue

        tworktime,maxsalary=0,0

        for i in xrange(wn):
            w=jsonobj["workExperienceList"][i]
            if w is None: continue

            _,position_name=format_position(w["position_name"])
            industry_name=format_industry(w["industry"])
            salary=int(w["salary"])
            if salary>maxsalary: maxsalary=salary

            if industry_name not in industry_salary: industry_salary[industry_name]=[salary]
            else: industry_salary[industry_name].append(salary)
            if position_name not in position_salary: position_salary[position_name]=[salary]
            else: position_salary[position_name].append(salary)

            if w["start_date"] is None or w["end_date"] is None: continue
            else:
                sd=w["start_date"].replace(" ","")
                ed=w["end_date"].replace(" ","")
            worktime=date_diff(sd,ed)
            tworktime+=worktime

        age,outlist=human_feat(jsonobj)
        if isTrain and (age==100 or age-tworktime/12>30 or age-tworktime/12<16): continue

        if outlist[1] not in major_salary: major_salary[outlist[1]]=[maxsalary]
        else: major_salary[outlist[1]].append(maxsalary)

    for k,v in major_salary.iteritems():
        val,a=[],np.array(v)
        for i in xrange(20,100,20):
            val.append(np.percentile(a,i))
        major_salary[k]=val

    for k,v in industry_salary.iteritems():
        val,a=[],np.array(v)
        for i in xrange(20,100,20):
            val.append(np.percentile(a,i))
        industry_salary[k]=val

    for k,v in position_salary.iteritems():
        val,a=[],np.array(v)
        for i in xrange(20,100,20):
            val.append(np.percentile(a,i))
        position_salary[k]=val

    # make feature sample by sample
    for sample in samples:
        jsonobj=json.loads(sample)
        wn=len(jsonobj["workExperienceList"])
        # if train, but work experience less than 3
        if isTrain and wn<3: continue

        tworktime,tsalary,maxposlevel,maxsalary,maxsalary_industry,maxsalary_position=0,0,0,0,0,0
        industryset=set()

        # iterate every work experience
        for i in xrange(wn):
            w=jsonobj["workExperienceList"][i]
            # if test, skip column that to be predicted
            if w is None: continue

            # position name
            poslevel,position_name=format_position(w["position_name"])
            if i==wn-1: first_poslevel=poslevel

            # industry
            industry_name=format_industry(w["industry"])
            industryset.add(industry_name)
            if i==wn-1: first_industry=industry_name

            # size
            size=int(w["size"])
            if i==wn-1: first_size=size

            # salary
            salary=int(w["salary"])
            if i==wn-1: first_salary=salary
            tsalary+=10*salary
            if salary>maxsalary:
                maxsalary=salary
                maxsalary_industry=industry_name
                maxsalary_position=position_name

            # worktime
            if w["start_date"] is None or w["end_date"] is None: continue
            else:
                sd=w["start_date"].replace(" ","")
                ed=w["end_date"].replace(" ","")
            worktime=date_diff(sd,ed)
            tworktime+=worktime

            if poslevel>=maxposlevel:
                firstmaxposworktime=tworktime
                maxposlevel=poslevel

            # label
            if isTrain and i==1: _,yposition=format_position(w["position_name"])

        # start join feature
        age,outlist=human_feat(jsonobj)

        # skip after feature generation
        if isTrain and (age==100 or age-tworktime/12>30 or age-tworktime/12<16): continue

        # using 3 percentile
        major_salarylevel,industry_salarylevel,position_salarylevel=0,0,0
        for percent in major_salary[outlist[1]]:
            if maxsalary>=percent: major_salarylevel+=1
        for percent in industry_salary[maxsalary_industry]:
            if maxsalary>=percent: industry_salarylevel+=1
        for percent in position_salary[maxsalary_position]:
            if maxsalary>=percent: position_salarylevel+=1

        # id,major,gender,first_work_age,first_industry,first_size,first_salary,first_poslevel,
        # total_worktime_per_work,total_worktime_per_industry,average_salary,firstmaxposworktime
        # salary_in_major_level,salary_in_industry_level,salary_in_position_level
        featlist=outlist[:3]+[age-tworktime/12,first_industry,first_size,first_salary,first_poslevel,tworktime/wn,
                              tworktime/len(industryset),tsalary/wn,(tworktime-firstmaxposworktime)/12,
                              major_salarylevel,industry_salarylevel,position_salarylevel]

        # if train, print label column
        if isTrain:
            featlist+=[jsonobj["degree"]]

        # skip position_name label not in [1-32]
        if isTrain and yposition==0: continue

        fout.write(",".join(map(str,featlist))+"\n")

    fout.close()

if __name__=="__main__":
    print "make train feat..."
    make_feat("../data/train"+VERSION+".json","../out/train_degree_"+VERSION+".csv")
    print "make test feat..."
    make_feat("../data/test.json","../out/test_degree_"+VERSION+".csv",False)
    # for p in otherposition:
    #     print p